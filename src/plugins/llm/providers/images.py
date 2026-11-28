"""OpenAI Image API 客户端

只给使用 `openai_images` 接口的生图模型用。这个接口不能对话，所以不继承对话用的 `Provider`，
也不注册到对话接口表里。生成使用 `/images/generations`，官方接入可使用 `/images/edits` 上传参考图。
"""

from __future__ import annotations

import base64
import binascii
import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx

from ..schemas import ImageContent, Usage
from .base import USER_AGENT, ImageResponseError, ProviderError, _decode_json_response, raise_for_error

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..config import ModelConfig
    from ..schemas import Message


@dataclass
class GeneratedImages:
    """一次图片生成的结果"""

    images: list[ImageContent] = field(default_factory=list)
    """生成的图片"""
    usage: Usage | None = None
    """图片接口返回的 token 用量；服务未提供时为空"""
    continuation: Message | None = None
    """可在同一 Responses 接入内回放的原生图片记录"""


_EDIT_INPUTS = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
_EDIT_FIELDS = frozenset(
    {
        "background",
        "complexity",
        "frame_count",
        "frame_duration_ms",
        "input_fidelity",
        "n",
        "output_compression",
        "output_format",
        "quality",
        "size",
    }
)


class ImagesClient:
    """OpenAI Image API 客户端。"""

    def __init__(self, config: ModelConfig, *, session_affinity: str = "") -> None:
        self.config = config
        self.session_affinity = session_affinity

    @property
    def endpoint(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/images/generations"

    def build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        if self.session_affinity:
            headers["X-Session-Affinity"] = self.session_affinity
        return headers

    async def generate(self, prompt: str) -> GeneratedImages:
        """按提示词生成图片"""
        payload: dict[str, Any] = {
            **copy.deepcopy(self.config.extra_body),
            "model": self.config.model,
            "prompt": prompt,
        }
        try:
            async with httpx.AsyncClient(proxy=self.config.proxy) as client:
                response = await client.post(
                    self.endpoint,
                    headers=self.build_headers(),
                    json=payload,
                    timeout=self.config.timeout,
                )
        except httpx.TimeoutException as e:
            raise ProviderError("图片生成请求超时，请稍后重试") from e
        except httpx.HTTPError as e:
            raise ProviderError(f"图片生成请求失败：{e}") from e
        data = _decode_json_response(response)
        raise_for_error(data, response.status_code)
        return self._parse_images(data)

    async def edit(self, prompt: str, references: Sequence[ImageContent]) -> GeneratedImages:
        """用 multipart 提交本轮参考图；不传兼容网关专用字段。"""
        if not 1 <= len(references) <= 16:
            raise ProviderError("官方改图请求须包含 1 至 16 张参考图")
        files = []
        for index, reference in enumerate(references, 1):
            extension = _EDIT_INPUTS.get(reference.mimetype)
            if not extension:
                raise ProviderError(f"第 {index} 张参考图格式不受支持；请使用 PNG、JPEG 或 WebP 静态图片")
            if len(reference.data) >= 50_000_000:
                raise ProviderError(f"第 {index} 张参考图须小于 50 MB")
            files.append(("image[]", (f"reference-{index}.{extension}", reference.data, reference.mimetype)))
        form = {k: v for k, v in self.config.extra_body.items() if k in _EDIT_FIELDS and v is not None}
        form.update(model=self.config.model, prompt=prompt)
        headers = self.build_headers()
        headers.pop("Content-Type")  # HTTPX supplies the multipart boundary.
        try:
            async with httpx.AsyncClient(proxy=self.config.proxy) as client:
                response = await client.post(
                    f"{self.config.base_url.rstrip('/')}/images/edits",
                    headers=headers,
                    data=form,
                    files=files,
                    timeout=self.config.timeout,
                )
        except httpx.TimeoutException as e:
            raise ProviderError("图片编辑请求超时，请稍后重试") from e
        except httpx.HTTPError as e:
            raise ProviderError(f"图片编辑请求失败：{e}") from e
        data = _decode_json_response(response)
        raise_for_error(data, response.status_code)
        return self._parse_images(data)

    def _parse_images(self, data: dict[str, Any]) -> GeneratedImages:
        usage = self._parse_usage(data.get("usage"))
        items = data.get("data")
        if not isinstance(items, list) or not items:
            raise ImageResponseError("图片接口没有返回图片数据", usage)
        images: list[ImageContent] = []
        for item in items:
            encoded = item.get("b64_json") if isinstance(item, dict) else None
            if not encoded:
                raise ImageResponseError("图片接口没有返回 base64 数据", usage)
            try:
                raw = base64.b64decode(encoded, validate=True)
                images.append(ImageContent.from_bytes(raw))
            except (binascii.Error, TypeError, ValueError) as e:
                raise ImageResponseError("生成图片的数据无效或格式不受支持", usage) from e
        return GeneratedImages(images=images, usage=usage)

    @staticmethod
    def _parse_usage(raw: object) -> Usage | None:
        if not isinstance(raw, dict) or not raw.keys() & {"input_tokens", "output_tokens"}:
            return None
        return Usage(
            input_tokens=int(raw.get("input_tokens") or 0),
            output_tokens=int(raw.get("output_tokens") or 0),
        )
