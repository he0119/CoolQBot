"""为本轮绘图选模型、确定请求规格并核验交付结果。"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from time import perf_counter
from typing import TYPE_CHECKING

from nonebot import logger
from PIL import Image

from .config import ModelCapability, ModelConfig, plugin_config
from .data_source import get_image_model_candidates
from .image_requirements import DEFAULT_SHORT_EDGE, HD_SIZE, SIZE_PATTERN, ImageRequirements
from .providers import (
    ImageCapabilities,
    ImageRequestOptions,
    ImageResponseError,
    ProviderError,
    generate_images,
    get_image_capabilities,
    image_options_error,
)
from .providers.openai_image_limits import aligned_ratio_size
from .schemas import ImageContent, ImageResult, Message

if TYPE_CHECKING:
    from collections.abc import Sequence


def _size_at_short_edge(ratio: tuple[int, int], edge: int) -> str:
    short = min(ratio)
    width, height = ((part * edge + short // 2) // short for part in ratio)
    return f"{width}x{height}"


def _model_default_edge(size: str) -> int:
    if SIZE_PATTERN.fullmatch(size):
        return min(map(int, size.split("x")))
    return DEFAULT_SHORT_EDGE


def _gif_preset(model: ModelConfig, default_size: str, short_edge: int, ratio: tuple[int, int] | None) -> str:
    formats = model.image_sizes_by_format.get("gif")
    presets = model.image_gif_size_presets or formats or set()
    restriction = formats if formats is not None else model.image_sizes or None
    if restriction is not None:
        presets = presets & restriction
    if ratio is None and default_size in presets:
        return default_size
    width_ratio, height_ratio = ratio or (1, 1)
    matching: list[tuple[int, int, str]] = []
    for value in presets:
        width, height = map(int, value.split("x"))
        if width * height_ratio == height * width_ratio:
            edge = min(width, height)
            matching.append((abs(edge - short_edge), -edge, value))
    return min(matching)[2] if matching else ""


def _resolve_size(
    requirements: ImageRequirements, model: ModelConfig, capabilities: ImageCapabilities, output_format: str
) -> str:
    if requirements.size:
        if requirements.hd and output_format != "gif" and requirements.size != HD_SIZE:
            raise ProviderError(f"--hd 固定为 {HD_SIZE}，与 --size {requirements.size} 冲突")
        return requirements.size
    ratio = requirements.aspect_ratio
    if requirements.hd:
        if output_format == "gif" and capabilities.auto_size:
            return "auto"
        if not ratio:
            return HD_SIZE
        if capabilities.official_geometry:
            return aligned_ratio_size(ratio, int(HD_SIZE.split("x")[0]), fit_hd=output_format != "gif")
        return _size_at_short_edge(ratio, int(HD_SIZE.split("x")[0]))
    default_size = capabilities.defaults.size
    edge = _model_default_edge(default_size)
    if output_format == "gif" and capabilities.explicit_frames:
        if preset := _gif_preset(model, default_size, edge, ratio):
            return preset
    if ratio:
        if capabilities.official_geometry:
            return aligned_ratio_size(ratio, edge, fit_hd=False)
        return _size_at_short_edge(ratio, edge)
    format_sizes = model.image_sizes_by_format.get(output_format, set())
    if len(format_sizes) == 1 and default_size not in format_sizes:
        return next(iter(format_sizes))
    return ""


def format_image_failure(error: Exception) -> str:
    text = f"绘图失败：{error}"
    if isinstance(error, ImageResponseError) and error.usage is not None:
        text += f"\n生图用量：{error.usage.to_chinese()}"
    return text


@dataclass(frozen=True)
class ImageTask:
    """根据本轮用户要求与选中的模型确定的单次请求。"""

    model: ModelConfig
    options: ImageRequestOptions
    expected_format: str
    expected_frames: int | None = None
    expected_ratio: tuple[int, int] | None = None

    def verify(self, images: list[ImageContent]) -> str:
        size = self.options.size
        if not (self.expected_format or size or self.expected_ratio):
            return ""
        details: list[str] = []
        for number, image in enumerate(images, start=1):
            try:
                with Image.open(BytesIO(image.data)) as decoded:
                    actual_format = (decoded.format or "未知格式").lower()
                    width, height = decoded.size
                    actual_size = f"{width}x{height}"
                    frames = getattr(decoded, "n_frames", 1) if actual_format == "gif" else 1
                    decoded.verify()
            except (OSError, ValueError, Image.DecompressionBombError) as error:
                raise ProviderError(f"第 {number} 张图片无法核验格式或尺寸") from error
            if self.expected_format and self.expected_format != actual_format:
                raise ProviderError(f"第 {number} 张图片要求 {self.expected_format}，服务返回 {actual_format}")
            if size and size != "auto" and size != actual_size:
                raise ProviderError(f"第 {number} 张图片要求 {size}，服务返回 {actual_size}")
            if self.expected_ratio:
                a, b = self.expected_ratio
                if width * b != height * a:
                    raise ProviderError(f"第 {number} 张图片要求宽高比 {a}:{b}，服务返回 {actual_size}")
            if actual_format == "gif" and frames < 2:
                raise ProviderError(f"第 {number} 张图片要求多帧 GIF，服务返回 {frames} 帧")
            if self.expected_frames is not None and frames != self.expected_frames:
                raise ProviderError(f"第 {number} 张图片要求 {self.expected_frames} 帧 GIF，服务返回 {frames} 帧")
            suffix = f" / {frames} 帧" if actual_format == "gif" else ""
            details.append(f"{actual_format.upper()} {actual_size}{suffix}")
        return "、".join(dict.fromkeys(details))

    async def run(
        self,
        prompt: str,
        *,
        session_affinity: str,
        images: list[ImageContent] | None = None,
        history: Sequence[Message] = (),
    ) -> tuple[ImageResult, Message | None]:
        if not prompt.strip():
            raise ProviderError("请提供绘图描述")
        started_at = perf_counter()
        try:
            generated = await generate_images(
                self.model,
                prompt,
                options=self.options,
                session_affinity=session_affinity,
                images=images,
                history=history,
            )
        except ImageResponseError as error:
            if error.usage is not None:
                logger.info("LLM 图片请求返回不可交付结果（模型={}，{}）", self.model.name, error.usage.to_chinese())
            raise
        elapsed = perf_counter() - started_at
        try:
            details = self.verify(generated.images)
        except ProviderError as error:
            result = ImageResult(self.model.name, generated.images, generated.usage, elapsed)
            logger.info("LLM 图片请求返回不可交付结果（{}）", result.summary())
            raise ImageResponseError(str(error), generated.usage) from error
        result = ImageResult(self.model.name, generated.images, generated.usage, elapsed, details)
        logger.info("LLM 图片请求完成（{}）", result.summary())
        return result, generated.continuation


def prepare_image(
    model: ModelConfig,
    requirements: ImageRequirements,
    *,
    use_context: bool = False,
    references: bool = False,
) -> ImageTask:
    """把用户的绘图要求转换为指定模型支持的请求。"""
    if ModelCapability.IMAGE_GENERATION not in model.capabilities:
        raise ProviderError("未声明 image_generation 能力，不能生成图片")
    if not model.base_url:
        raise ProviderError("未配置 base_url，且未设置 LLM__BASE_URL")
    capabilities = get_image_capabilities(model)
    if use_context and not capabilities.continuation:
        raise ProviderError("不支持 -c 多轮续画，请用支持续画的模型，或回复具体图片改图")
    if references and not capabilities.references:
        raise ProviderError("此生图模型不支持参考图")

    defaults = capabilities.defaults
    output_format = requirements.output_format or defaults.output_format or "png"
    size = _resolve_size(requirements, model, capabilities, output_format)
    ratio = requirements.aspect_ratio
    if capabilities.official_geometry and output_format != "gif" and ratio and max(ratio) > 3 * min(ratio):
        raise ProviderError("官方 Images 宽高比必须在 1:3 至 3:1 之间")
    options = ImageRequestOptions(
        output_format=requirements.output_format, size=size, frame_count=requirements.frame_count
    )
    if error := image_options_error(model, options):
        raise ProviderError(error)

    expected_format = requirements.output_format or ("gif" if output_format == "gif" else "")
    expected_frames = requirements.frame_count
    if expected_frames is None and output_format == "gif" and capabilities.explicit_frames:
        expected_frames = defaults.frame_count
    return ImageTask(model, options, expected_format, expected_frames, ratio if size == "auto" else None)


async def select_image_task(
    session_id: str,
    requirements: ImageRequirements,
    *,
    selected_name: str = "",
    use_context: bool = False,
    references: bool = False,
) -> ImageTask:
    enabled, candidates = await get_image_model_candidates(session_id)
    if selected_name:
        if selected_name not in enabled:
            raise ProviderError(f"本群未启用的模型：{selected_name}")
        candidates = [selected_name]
    if not candidates:
        raise ProviderError("本群未启用生图模型，请联系超级管理员启用并设置")
    reasons = []
    for name in candidates:
        try:
            return prepare_image(
                plugin_config.resolve(name), requirements, use_context=use_context, references=references
            )
        except ProviderError as error:
            reasons.append(f"{name}：{error}")
    ratio = requirements.aspect_ratio
    geometry = f"{ratio[0]}:{ratio[1]}" if ratio else requirements.size
    requested = " / ".join(filter(None, (requirements.output_format.upper(), geometry)))
    if requested:
        reasons.insert(0, f"要求 {requested}")
    raise ProviderError("本群没有满足绘图要求的模型（" + "；".join(reasons) + "）")
