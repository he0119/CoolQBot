"""OpenAI Image API 客户端

只用于声明了 `image_generation` 能力的生图模型，不参与对话。
请求 `POST {base_url}/images/generations`，返回的 `b64_json` 解码后交给调用方。
"""

from __future__ import annotations

import base64
import binascii
import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NoReturn

import httpx

from ..schemas import ImageContent, Usage
from .base import USER_AGENT, Provider, ProviderError, _decode_json_response

if TYPE_CHECKING:
    from ..schemas import Message, ToolChoice, ToolParam


@dataclass
class GeneratedImages:
    """一次图片生成的结果"""

    images: list[ImageContent] = field(default_factory=list)
    """生成的图片"""
    usage: Usage = field(default_factory=Usage)
    """图片接口返回的 token 用量"""


class ImagesProvider(Provider):
    """生图模型使用的 Image API，不参与文本对话"""

    @property
    def endpoint(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/images/generations"

    def build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def build_payload(
        self,
        messages: list[Message],
        tools: list[ToolParam] | None = None,
        stream: bool = False,
        tool_choice: ToolChoice = "auto",
    ) -> dict[str, Any]:
        raise ProviderError(f"模型 {self.config.name} 使用 openai_images 接口，只用于图片生成，不能对话")

    def parse_response(self, data: dict[str, Any]) -> NoReturn:
        raise ProviderError(f"模型 {self.config.name} 使用 openai_images 接口，只用于图片生成，不能对话")

    async def parse_stream(self, response: httpx.Response) -> NoReturn:
        raise ProviderError(f"模型 {self.config.name} 使用 openai_images 接口，只用于图片生成，不能对话")

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolParam] | None = None,
        *,
        tool_choice: ToolChoice = "auto",
    ) -> NoReturn:
        raise ProviderError(f"模型 {self.config.name} 使用 openai_images 接口，只用于图片生成，不能对话")

    async def generate(self, prompt: str) -> GeneratedImages:
        """按提示词生成图片"""
        payload: dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            **copy.deepcopy(self.config.extra_body),
        }
        headers = self.build_headers()
        headers["User-Agent"] = USER_AGENT
        if self.session_affinity:
            headers["X-Session-Affinity"] = self.session_affinity
        try:
            async with httpx.AsyncClient(proxy=self.config.proxy) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout,
                )
        except httpx.TimeoutException as e:
            raise ProviderError("图片生成请求超时，请稍后重试") from e
        except httpx.HTTPError as e:
            raise ProviderError(f"图片生成请求失败：{e}") from e
        data = _decode_json_response(response)
        self.raise_for_error(data, response.status_code)
        return self._parse_images(data)

    def _parse_images(self, data: dict[str, Any]) -> GeneratedImages:
        items = data.get("data")
        if not isinstance(items, list) or not items:
            raise ProviderError("图片接口没有返回图片数据")
        images: list[ImageContent] = []
        for item in items:
            encoded = item.get("b64_json") if isinstance(item, dict) else None
            if not encoded:
                raise ProviderError("图片接口没有返回 base64 数据")
            try:
                raw = base64.b64decode(encoded, validate=True)
                images.append(ImageContent.from_bytes(raw))
            except (binascii.Error, TypeError, ValueError) as e:
                raise ProviderError("生成图片的数据无效或格式不受支持") from e
        usage = self._parse_usage(data.get("usage"))
        return GeneratedImages(images=images, usage=usage)

    @staticmethod
    def _parse_usage(raw: dict[str, Any] | None) -> Usage:
        if not raw:
            return Usage()
        return Usage(
            input_tokens=int(raw.get("input_tokens") or 0),
            output_tokens=int(raw.get("output_tokens") or 0),
        )
