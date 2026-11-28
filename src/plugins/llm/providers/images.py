"""OpenAI Image API 客户端

只给使用 `openai_images` 接口的生图模型用。这个接口不能对话，所以不继承对话用的 `Provider`，
也不注册到对话接口表里。生成使用 `/images/generations`，官方接入可使用 `/images/edits` 上传参考图。
"""

from __future__ import annotations

import base64
import binascii
from typing import TYPE_CHECKING, Any

import httpx

from ..schemas import ImageContent, Usage
from .base import USER_AGENT, ImageResponseError, ProviderError, _decode_json_response, raise_for_error
from .image_options import (
    ANIMATION_FIELDS,
    FRAME_COUNT_ERROR,
    GeneratedImages,
    ImageCapabilities,
    ImageRequestOptions,
    configured_image_defaults,
    declared_options_error,
)
from .openai_image_limits import (
    is_official_endpoint,
    supports_official_gif,
    supports_official_image_edits,
    uses_official_image_api,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..config import ModelConfig
    from ..schemas import Message


_EDIT_INPUTS = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
_EDIT_FIELDS = frozenset(
    {
        "background",
        "complexity",
        "frame_count",
        "frame_duration_ms",
        "input_fidelity",
        "moderation",
        "n",
        "output_compression",
        "output_format",
        "quality",
        "safety_identifier",
        "size",
        "user",
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

    def image_capabilities(self) -> ImageCapabilities:
        model, body = self.config, self.config.extra_body
        references = supports_official_image_edits(model.base_url, model.model)
        native_gif = supports_official_gif(model.base_url, model.model)
        gif_declared = "gif" in model.image_output_formats or body.get("output_format") == "gif"
        gif = gif_declared and (native_gif or not is_official_endpoint(model.base_url))
        return ImageCapabilities(
            references=references,
            continuation=False,
            gif=gif,
            explicit_frames=gif and native_gif,
            auto_size=references,
            official_geometry=uses_official_image_api(model.base_url, model.model),
            defaults=configured_image_defaults(body, animated=gif),
        )

    def image_options_error(self, options: ImageRequestOptions) -> str:
        return self._options_error(options, options.apply(self.config.extra_body))

    def _options_error(self, options: ImageRequestOptions, effective: dict[str, Any]) -> str:
        capabilities = self.image_capabilities()
        animated = effective.get("output_format") == "gif"
        if animated and not capabilities.gif:
            if is_official_endpoint(self.config.base_url) and not supports_official_gif(
                self.config.base_url, self.config.model
            ):
                return "此官方 Images 模型不支持动态 GIF"
            return "未声明支持 gif 格式"
        if options.frame_count is not None:
            if not animated:
                return "--frames 仅适用于 GIF"
            if not capabilities.explicit_frames:
                return "指定 GIF 帧数仅支持官方 Images 直连"
        if error := declared_options_error(
            self.config, options, effective, capabilities, native_static=capabilities.references
        ):
            return error
        if animated and capabilities.explicit_frames:
            frames = effective.get("frame_count")
            if frames is not None and (type(frames) is not int or not 2 <= frames <= 16):
                return FRAME_COUNT_ERROR
            duration = effective.get("frame_duration_ms")
            if duration is not None and (type(duration) is not int or not 20 <= duration <= 2000):
                return "官方 GIF 每帧时长必须是 20 至 2000 毫秒的整数"
            if (
                effective.get("stream")
                or effective.get("partial_images")
                or effective.get("output_compression") is not None
            ):
                return "官方 GIF 不支持流式、部分图片或自定义压缩"
        return ""

    def _request_parameters(self, options: ImageRequestOptions) -> dict[str, Any]:
        parameters = options.apply(self.config.extra_body)
        if error := self._options_error(options, parameters):
            raise ProviderError(error)
        if parameters.get("output_format") != "gif":
            for key in ANIMATION_FIELDS:
                parameters.pop(key, None)
        return parameters

    async def generate_images(
        self,
        prompt: str,
        *,
        options: ImageRequestOptions,
        images: list[ImageContent] | None = None,
        history: Sequence[Message] = (),
    ) -> GeneratedImages:
        if history:
            raise ProviderError("此生图模型不支持多轮续画，请回复具体图片改图")
        if images:
            return await self.edit(prompt, images, options=options)
        return await self.generate(prompt, options=options)

    async def generate(self, prompt: str, *, options: ImageRequestOptions = ImageRequestOptions()) -> GeneratedImages:
        """按提示词生成图片。"""
        payload = self._request_parameters(options)
        payload.update(model=self.config.model, prompt=prompt)
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

    async def edit(
        self, prompt: str, references: Sequence[ImageContent], *, options: ImageRequestOptions = ImageRequestOptions()
    ) -> GeneratedImages:
        """以多部分表单上传本轮参考图及官方改图参数。"""
        if not self.image_capabilities().references:
            raise ProviderError("此生图模型仅支持生成，不能使用参考图")
        parameters = self._request_parameters(options)
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
        form = {key: value for key, value in parameters.items() if key in _EDIT_FIELDS and value is not None}
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
