"""从 Wikimedia Commons 获取带授权信息的美食图片。"""

import html
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import TypeGuard
from urllib.parse import urljoin, urlparse

import httpx
from nonebot import logger

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
COMMONS_USER_AGENT = "CoolQBot (+https://github.com/he0119/CoolQBot)"
COMMONS_THUMBNAIL_HOST = "upload.wikimedia.org"
COMMONS_PAGE_HOST = "commons.wikimedia.org"
COMMONS_IMAGE_WIDTH = 640
MAX_IMAGE_BYTES = 3 * 1024 * 1024
IMAGE_CACHE_SIZE = 32
SUPPORTED_IMAGE_TYPES = {"image/gif", "image/jpeg", "image/png", "image/webp"}
SAFE_LICENSE_HOSTS = {"commons.wikimedia.org", "creativecommons.org", "www.gnu.org"}

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_IMAGE_CACHE: OrderedDict[str, "FoodImage"] = OrderedDict()


@dataclass(frozen=True)
class FoodImage:
    """可直接发送的美食图片及其署名信息。"""

    content: bytes
    mimetype: str
    creator: str
    license_name: str
    source_url: str
    license_url: str | None = None

    @property
    def attribution(self) -> str:
        """生成随图片发送的署名文本。"""
        lines = [f"图片：{self.creator}｜{self.license_name}", f"来源：{self.source_url}"]
        if self.license_url:
            lines.append(f"许可：{self.license_url}")
        return "\n".join(lines)


def _plain_text(value: object, default: str, max_length: int) -> str:
    if not isinstance(value, str):
        return default
    text = html.unescape(_HTML_TAG_PATTERN.sub("", value)).strip()
    return text[:max_length] or default


def _metadata_value(metadata: object, key: str) -> str | None:
    if not isinstance(metadata, dict):
        return None
    item = metadata.get(key)
    if not isinstance(item, dict):
        return None
    value = item.get("value")
    return value if isinstance(value, str) else None


def _is_https_url(url: object, allowed_hosts: set[str]) -> TypeGuard[str]:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in allowed_hosts and not parsed.username and not parsed.password


def _safe_license_url(value: str | None) -> str | None:
    if not value:
        return None
    url = urljoin(f"https://{COMMONS_PAGE_HOST}", value)
    return url if _is_https_url(url, SAFE_LICENSE_HOSTS) else None


def _parse_file_result(payload: object) -> tuple[str, str, str, str, str, str | None] | None:
    if not isinstance(payload, dict):
        return None
    query = payload.get("query")
    if not isinstance(query, dict):
        return None
    pages = query.get("pages")
    if isinstance(pages, dict):
        page_values = pages.values()
    elif isinstance(pages, list):
        page_values = pages
    else:
        return None

    for page in (page for page in page_values if isinstance(page, dict)):
        image_info = page.get("imageinfo")
        if not isinstance(image_info, list) or not image_info or not isinstance(image_info[0], dict):
            continue
        info = image_info[0]
        mimetype = info.get("mime")
        thumbnail_url = info.get("thumburl")
        source_url = info.get("descriptionurl")
        if not isinstance(mimetype, str) or mimetype not in SUPPORTED_IMAGE_TYPES:
            continue
        if not _is_https_url(thumbnail_url, {COMMONS_THUMBNAIL_HOST}):
            continue
        if not _is_https_url(source_url, {COMMONS_PAGE_HOST}):
            continue

        metadata = info.get("extmetadata")
        creator = _plain_text(_metadata_value(metadata, "Artist"), "未知作者", 100)
        license_name = _plain_text(_metadata_value(metadata, "LicenseShortName"), "授权信息见来源页", 60)
        license_url = _safe_license_url(_metadata_value(metadata, "LicenseUrl"))
        return thumbnail_url, mimetype, creator, license_name, source_url, license_url
    return None


async def _download_image(client: httpx.AsyncClient, url: str) -> tuple[bytes, str] | None:
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        mimetype = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if mimetype not in SUPPORTED_IMAGE_TYPES:
            return None

        content_length = response.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_IMAGE_BYTES:
            return None

        content = bytearray()
        async for chunk in response.aiter_bytes():
            content.extend(chunk)
            if len(content) > MAX_IMAGE_BYTES:
                return None
        return bytes(content), mimetype


def _cache_image(file_title: str, image: FoodImage) -> None:
    _IMAGE_CACHE[file_title] = image
    _IMAGE_CACHE.move_to_end(file_title)
    while len(_IMAGE_CACHE) > IMAGE_CACHE_SIZE:
        _IMAGE_CACHE.popitem(last=False)


async def get_food_image(file_title: str) -> FoodImage | None:
    """按文件标题下载一张 Wikimedia Commons 美食缩略图。"""
    if cached := _IMAGE_CACHE.get(file_title):
        _IMAGE_CACHE.move_to_end(file_title)
        return cached

    params = {
        "action": "query",
        "titles": file_title,
        "redirects": 1,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": COMMONS_IMAGE_WIDTH,
        "format": "json",
        "formatversion": 2,
    }
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": COMMONS_USER_AGENT},
            timeout=10,
            follow_redirects=False,
        ) as client:
            response = await client.get(COMMONS_API_URL, params=params)
            response.raise_for_status()
            result = _parse_file_result(response.json())
            if not result:
                return None
            thumbnail_url, expected_mimetype, creator, license_name, source_url, license_url = result
            downloaded = await _download_image(client, thumbnail_url)
            if not downloaded:
                return None
            content, mimetype = downloaded
            if mimetype != expected_mimetype:
                logger.debug("Commons 美食图片格式与元数据不同：文件={}，实际格式={}", file_title, mimetype)
            image = FoodImage(
                content=content,
                mimetype=mimetype,
                creator=creator,
                license_name=license_name,
                source_url=source_url,
                license_url=license_url,
            )
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        logger.warning("Commons 美食图片获取失败：文件={}，回退为纯文字", file_title)
        return None

    _cache_image(file_title, image)
    return image
