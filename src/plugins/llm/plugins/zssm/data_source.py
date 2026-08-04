"""“这是什么”解释模式的数据准备。"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from nonebot.log import logger
from nonebot_plugin_alconna import image_fetch

from ...config import plugin_config
from ...handler import LLMHandler, split_content
from ...schemas import Completion, ImageContent
from ...tools.web import ResourceContent, ResourceError, read_resource, resource_log_target

if TYPE_CHECKING:
    from nonebot.adapters import Bot, Event
    from nonebot.typing import T_State
    from nonebot_plugin_alconna.uniseg import Image

URL_PATTERN = re.compile(r"https?://[^\s<>\"'，。；：！？、（）【】《》「」『』]+", re.IGNORECASE)
TRAILING_URL_PUNCTUATION = ".,;:!?，。；：！？、)]}）】》」』"
VISION_PROMPT = Path(__file__).with_name("vision_prompt.txt").read_text(encoding="utf-8")


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


def resolve_vision_fallback(model_name: str, vision_model_name: str, *, has_images: bool) -> str:
    """按模型能力决定是否需要独立视觉模型。"""
    if not has_images or "vision" in plugin_config.get_model(model_name).capabilities:
        return ""

    if not vision_model_name:
        raise ValueError("解释模型未声明 vision 能力，且本群没有已启用并声明 vision 能力的模型")
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

    if images:
        logger.info("开始读取 {} 张图片", len(images))
    contents: list[ImageContent] = []
    for image in images:
        data = await image_fetch(event, bot, state, image)
        if not data:
            raise ValueError("图片读取失败")
        if len(data) > plugin_config.zssm_max_image_bytes:
            limit = plugin_config.zssm_max_image_bytes / 1024 / 1024
            raise ValueError(f"图片超过 {limit:g} MiB 限制")
        contents.append(ImageContent.from_bytes(data))
    if contents:
        logger.info("已读取 {} 张图片，共 {} 字节", len(contents), sum(len(item.data) for item in contents))
    return contents


async def describe_images(model_name: str, images: list[ImageContent]) -> tuple[str, Completion]:
    """使用统一 LLM Provider 调用专用视觉模型描述图片。"""
    if "vision" not in plugin_config.get_model(model_name).capabilities:
        raise ValueError(f"视觉模型 {model_name} 未声明 vision 能力")
    logger.info("调用视觉模型 {} 描述 {} 张图片", model_name, len(images))
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
    logger.info("视觉模型 {} 已返回图片描述", completion.model)
    return description, completion


async def load_resources(*texts: str) -> list[ResourceContent]:
    """读取消息中实际出现的有限数量外部资源。"""
    urls = extract_urls(*texts)[: plugin_config.zssm_max_resources]
    if not urls:
        return []

    total = len(urls)

    async def load(index: int, url: str) -> ResourceContent:
        target = resource_log_target(url)
        logger.info("开始读取外部资源 {}/{}（{}）", index, total, target)
        try:
            resource = await read_resource(url)
        except ResourceError as e:
            logger.warning("读取外部资源失败 {}/{}（{}）：{}", index, total, target, e)
            return ResourceContent(url=url, kind="error", content=f"读取失败：{e}")
        logger.info(
            "外部资源读取完成 {}/{}（{}，{}，{} 字符）",
            index,
            total,
            resource_log_target(resource.url),
            resource.kind,
            len(resource.content),
        )
        return resource

    return list(await asyncio.gather(*(load(index, url) for index, url in enumerate(urls, start=1))))
