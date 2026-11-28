"""绘图接口共用的参数、声明和返回值。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .openai_image_limits import size_error

if TYPE_CHECKING:
    from ..config import ModelConfig
    from ..schemas import ImageContent, Message, Usage


_STATIC_FORMATS = frozenset({"png", "jpeg", "webp"})
_FORMATS = _STATIC_FORMATS | {"gif"}
_FIXED_OFFICIAL_SIZES = frozenset({"auto", "1024x1024", "1024x1536", "1536x1024"})
_SIZE_PATTERN = re.compile(r"[1-9][0-9]{0,4}x[1-9][0-9]{0,4}")
ANIMATION_FIELDS = frozenset({"frames", "frame_count", "frame_duration", "frame_duration_ms", "duration"})
FRAME_COUNT_ERROR = "官方 GIF 帧数必须是 2 至 16 之间的整数"


@dataclass(frozen=True)
class ImageRequestOptions:
    """本轮覆盖项。空字符串和 None 保留服务配置。"""

    output_format: str = ""
    size: str = ""
    frame_count: int | None = None

    def apply(self, parameters: dict[str, Any]) -> dict[str, Any]:
        result = dict(parameters)
        if self.output_format:
            result["output_format"] = self.output_format
        if self.size:
            result["size"] = self.size
        if self.frame_count is not None:
            result["frame_count"] = self.frame_count
        return result


@dataclass(frozen=True)
class ImageCapabilities:
    """绘图层可使用的能力及管理员设置的默认值。"""

    references: bool
    continuation: bool
    gif: bool
    explicit_frames: bool
    auto_size: bool
    official_geometry: bool
    defaults: ImageRequestOptions


@dataclass
class GeneratedImages:
    """一次图片生成的结果。"""

    images: list[ImageContent] = field(default_factory=list)
    usage: Usage | None = None
    """服务未返回 token 用量时为空。"""
    continuation: Message | None = None
    """可在同一 Responses 接入内回放的原生图片记录。"""


def configured_image_defaults(parameters: dict[str, Any], *, animated: bool = False) -> ImageRequestOptions:
    output_format = parameters.get("output_format")
    size = parameters.get("size")
    frames = parameters.get("frame_count") if animated else None
    return ImageRequestOptions(
        output_format=output_format if isinstance(output_format, str) else "",
        size=size if isinstance(size, str) else "",
        frame_count=frames if isinstance(frames, int) and not isinstance(frames, bool) else None,
    )


def declared_options_error(
    model: ModelConfig,
    options: ImageRequestOptions,
    effective: dict[str, Any],
    capabilities: ImageCapabilities,
    *,
    native_static: bool,
) -> str:
    """校验格式、尺寸及管理员声明。网关的私有默认尺寸原样传给网关。"""
    output_format = effective.get("output_format")
    if output_format is None or output_format == "":
        output_format = "png"
    if not isinstance(output_format, str) or output_format not in _FORMATS:
        return "图片格式仅支持 gif、png、jpeg、webp"
    default_format = capabilities.defaults.output_format
    if (
        options.output_format
        and output_format not in model.image_output_formats
        and output_format != default_format
        and not (native_static and not model.image_output_formats and output_format in _STATIC_FORMATS)
    ):
        return f"未声明支持 {output_format} 格式"

    if options.size == "auto" and not capabilities.auto_size:
        return "显式 --size auto 仅支持官方 Images 直连"
    if options.size and options.size != "auto" and not _SIZE_PATTERN.fullmatch(options.size):
        return f"换算出的尺寸 {options.size} 超出允许范围"

    size = effective.get("size")
    if size is None or size == "":
        size = "auto"
    if capabilities.official_geometry and size != "auto":
        if not isinstance(size, str) or not _SIZE_PATTERN.fullmatch(size):
            return "官方 Images 尺寸须为 WIDTHxHEIGHT 或 auto"
        width, height = map(int, size.split("x"))
        if error := size_error(width, height, animated=output_format == "gif"):
            return error
    if native_static and not capabilities.official_geometry:
        if not isinstance(size, str) or size not in _FIXED_OFFICIAL_SIZES:
            return "此官方 GPT Image 型号的尺寸仅支持 1024x1024、1024x1536、1536x1024 或 auto"
    if (format_sizes := model.image_sizes_by_format.get(output_format)) is not None:
        if not isinstance(size, str) or size not in format_sizes:
            available = "、".join(sorted(format_sizes)) or "无"
            return f"{output_format} 未声明支持 {size}，已配置尺寸：{available}"
    elif (
        options.size
        and options.size not in model.image_sizes
        and options.size != capabilities.defaults.size
        and not (native_static and not model.image_sizes)
    ):
        return f"未声明支持 {options.size} 尺寸"
    return ""
