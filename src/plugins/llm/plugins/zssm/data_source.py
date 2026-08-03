"""“这是什么”解释模式的数据准备与外部资源读取。"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import re
import socket
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast
from urllib.parse import urljoin, urlsplit

import httpx
import pymupdf
from nonebot_plugin_alconna import image_fetch

from ...config import plugin_config
from ...handler import LLMHandler, split_content
from ...providers.base import USER_AGENT
from ...schemas import Completion, ImageContent

if TYPE_CHECKING:
    from nonebot.adapters import Bot, Event
    from nonebot.typing import T_State
    from nonebot_plugin_alconna.uniseg import Image

URL_PATTERN = re.compile(r"https?://[^\s<>\"'，。；：！？、（）【】《》「」『』]+", re.IGNORECASE)
TRAILING_URL_PUNCTUATION = ".,;:!?，。；：！？、)]}）】》」』"
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
MAX_REDIRECTS = 5
VISION_PROMPT = Path(__file__).with_name("vision_prompt.txt").read_text(encoding="utf-8")


class ResourceError(Exception):
    """外部资源不能安全读取或无法解析。"""


@dataclass(frozen=True)
class ResourceContent:
    """交给模型的外部资源文本。"""

    url: str
    kind: str
    content: str


class _HTMLTextExtractor(HTMLParser):
    """从 HTML 中提取可见文本，不执行脚本和子资源请求。"""

    _SKIPPED_TAGS: ClassVar[set[str]] = {"script", "style", "noscript", "svg", "template"}
    _BLOCK_TAGS: ClassVar[set[str]] = {
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "p",
        "section",
        "table",
        "td",
        "th",
        "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in self._SKIPPED_TAGS:
            self._skip_depth += 1
        elif not self._skip_depth and tag in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIPPED_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif not self._skip_depth and tag in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._chunks.append(data)

    def text(self) -> str:
        lines = (" ".join(line.split()) for line in "".join(self._chunks).splitlines())
        return "\n".join(line for line in lines if line)


def extract_urls(*texts: str) -> list[str]:
    """按出现顺序提取并去重 HTTP(S) 链接。"""
    urls: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for match in URL_PATTERN.finditer(text):
            url = match.group(0).rstrip(TRAILING_URL_PUNCTUATION)
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def build_user_prompt(
    target: str,
    focus: str,
    image_count: int,
    resources: list[ResourceContent],
    image_descriptions: str = "",
) -> str:
    """把不可信聊天内容编码为 JSON 数据，避免与提示词指令混在一起。"""
    payload = {
        "target": target,
        "focus": focus,
        "image_count": image_count,
        "image_descriptions": image_descriptions,
        "resources": [asdict(resource) for resource in resources],
    }
    return json.dumps(payload, ensure_ascii=False)


def format_explain_response(content: str) -> str:
    """解析解释模式的 JSON 输出；格式异常时保留模型原文。"""
    raw = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw, re.IGNORECASE | re.DOTALL)
    if fenced:
        raw = fenced.group(1).strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if not isinstance(result, dict):
        return raw
    if result.get("blocked", False):
        return "（抱歉，我现在还不会这个）"

    output = result.get("output")
    if not isinstance(output, str) or not output.strip():
        return "（抱歉，我现在还不会这个）"

    keywords = result.get("keywords")
    if isinstance(keywords, list):
        keyword_text = " | ".join(
            dict.fromkeys(item.strip() for item in keywords if isinstance(item, str) and item.strip())
        )
        if keyword_text:
            return f"关键词：{keyword_text}\n\n{output.strip()}"
    return output.strip()


def resolve_vision_fallback(model_name: str, *, has_images: bool) -> str:
    """按模型能力决定是否需要独立视觉模型。"""
    if not has_images or "vision" in plugin_config.get_model(model_name).capabilities:
        return ""

    vision_model_name = plugin_config.zssm_vision_model
    if not vision_model_name:
        raise ValueError("解释模型未声明 vision 能力，请配置支持视觉输入的模型，或设置 LLM__ZSSM_VISION_MODEL")
    try:
        vision_model = plugin_config.get_model(vision_model_name)
    except ValueError as e:
        names = "、".join(plugin_config.get_model_names())
        raise ValueError(f"视觉模型未启用：{vision_model_name}，可用：{names}") from e
    if "vision" not in vision_model.capabilities:
        raise ValueError(f"视觉模型 {vision_model_name} 未声明 vision 能力")
    return vision_model_name


async def fetch_images(
    images: list[Image],
    event: Event,
    bot: Bot,
    state: T_State,
) -> list[ImageContent]:
    """通过 Alconna 的跨适配器下载器获取图片。"""
    if len(images) > plugin_config.zssm_max_images:
        raise ValueError(f"图片数量超过限制，最多 {plugin_config.zssm_max_images} 张")

    contents: list[ImageContent] = []
    for image in images:
        data = await image_fetch(event, bot, state, image)
        if not data:
            raise ValueError("图片读取失败")
        if len(data) > plugin_config.zssm_max_image_bytes:
            limit = plugin_config.zssm_max_image_bytes / 1024 / 1024
            raise ValueError(f"图片超过 {limit:g} MiB 限制")
        contents.append(ImageContent.from_bytes(data))
    return contents


async def describe_images(model_name: str, images: list[ImageContent]) -> tuple[str, Completion]:
    """使用统一 LLM Provider 调用专用视觉模型描述图片。"""
    if "vision" not in plugin_config.get_model(model_name).capabilities:
        raise ValueError(f"视觉模型 {model_name} 未声明 vision 能力")
    handler = LLMHandler(
        model_name,
        system_prompt=VISION_PROMPT,
        enable_tools=False,
        show_thinking=False,
    )
    completion = await handler.ask(f"请依次描述这 {len(images)} 张图片。", images)
    description, _ = split_content(completion)
    if not description:
        raise ValueError("视觉模型没有返回图片描述")
    return description, completion


async def load_resources(*texts: str) -> list[ResourceContent]:
    """读取消息中实际出现的有限数量外部资源。"""
    urls = extract_urls(*texts)[: plugin_config.zssm_max_resources]
    if not urls:
        return []

    async def load(url: str) -> ResourceContent:
        try:
            return await read_resource(url)
        except ResourceError as e:
            return ResourceContent(url=url, kind="error", content=f"读取失败：{e}")

    return list(await asyncio.gather(*(load(url) for url in urls)))


async def read_resource(url: str) -> ResourceContent:
    """安全下载并解析一个网页、纯文本或 PDF。"""
    data, content_type, final_url = await _download_resource(url)
    if data.startswith(b"%PDF-") or "application/pdf" in content_type:
        return ResourceContent(final_url, "pdf", _extract_pdf_text(data))

    if not (
        content_type.startswith("text/")
        or "application/json" in content_type
        or "application/xhtml+xml" in content_type
    ):
        raise ResourceError(f"不支持的内容类型 {content_type or 'unknown'}")

    text = _decode_text(data, content_type)
    if "html" in content_type or "xhtml" in content_type:
        parser = _HTMLTextExtractor()
        parser.feed(text)
        text = parser.text()
    else:
        text = _normalize_text(text)

    if not text:
        raise ResourceError("没有提取到可读文本")
    return ResourceContent(final_url, "web_page", _truncate(text))


async def _download_resource(url: str) -> tuple[bytes, str, str]:
    timeout = httpx.Timeout(plugin_config.zssm_resource_timeout)
    async with httpx.AsyncClient(
        proxy=plugin_config.zssm_resource_proxy,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        current_url = url
        for _ in range(MAX_REDIRECTS + 1):
            await _ensure_public_url(current_url)
            try:
                async with client.stream("GET", current_url, follow_redirects=False) as response:
                    if response.status_code in REDIRECT_STATUS_CODES:
                        location = response.headers.get("location")
                        if not location:
                            raise ResourceError("重定向响应缺少目标地址")
                        current_url = urljoin(str(response.url), location)
                        continue

                    response.raise_for_status()
                    if length := response.headers.get("content-length"):
                        try:
                            if int(length) > plugin_config.zssm_max_resource_bytes:
                                raise ResourceError("资源超过下载大小限制")
                        except ValueError:
                            pass

                    chunks: list[bytes] = []
                    total_size = 0
                    async for chunk in response.aiter_bytes():
                        total_size += len(chunk)
                        if total_size > plugin_config.zssm_max_resource_bytes:
                            raise ResourceError("资源超过下载大小限制")
                        chunks.append(chunk)
                    content_type = response.headers.get("content-type", "").lower()
                    return b"".join(chunks), content_type, str(response.url)
            except ResourceError:
                raise
            except httpx.TimeoutException as e:
                raise ResourceError("下载超时") from e
            except httpx.HTTPError as e:
                raise ResourceError(f"下载失败：{e}") from e
    raise ResourceError("重定向次数过多")


async def _ensure_public_url(url: str) -> None:
    """拒绝非 HTTP(S)、带凭据和解析到非公网地址的 URL。"""
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as e:
        raise ResourceError("URL 格式无效") from e
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ResourceError("仅支持 HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ResourceError("URL 不允许包含登录凭据")

    host = parsed.hostname
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        loop = asyncio.get_running_loop()
        try:
            records = await loop.getaddrinfo(
                host,
                port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except OSError as e:
            raise ResourceError("域名解析失败") from e
        addresses = {ipaddress.ip_address(record[4][0]) for record in records}

    if not addresses or any(not address.is_global for address in addresses):
        raise ResourceError("不允许访问本机、内网或非公网地址")


def _extract_pdf_text(data: bytes) -> str:
    try:
        with pymupdf.open(stream=data, filetype="pdf") as document:
            if document.needs_pass:
                raise ResourceError("PDF 需要密码")
            page_count = min(len(document), plugin_config.zssm_max_pdf_pages)
            text_parts: list[str] = []
            extracted_chars = 0
            for index in range(page_count):
                page_text = cast("str", document.load_page(index).get_text("text"))
                remaining = plugin_config.zssm_max_resource_chars + 1 - extracted_chars
                if remaining <= 0:
                    break
                text_parts.append(page_text[:remaining])
                extracted_chars += len(page_text[:remaining])
            text = "\n".join(text_parts)
    except ResourceError:
        raise
    except Exception as e:
        raise ResourceError("PDF 解析失败") from e

    text = _normalize_text(text)
    if not text:
        raise ResourceError("PDF 没有可提取的文字")
    return _truncate(text)


def _decode_text(data: bytes, content_type: str) -> str:
    charset = "utf-8"
    if match := re.search(r"charset=([^;\s]+)", content_type):
        charset = match.group(1).strip("\"'")
    try:
        return data.decode(charset, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")


def _normalize_text(text: str) -> str:
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _truncate(text: str) -> str:
    limit = plugin_config.zssm_max_resource_chars
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n……（内容过长，已截断）"
