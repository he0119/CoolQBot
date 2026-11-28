"""命令与聊天工具共用的图片任务、用量和专用续画历史。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from io import BytesIO
from math import gcd
from time import perf_counter
from typing import TYPE_CHECKING

from nonebot.log import logger
from PIL import Image

from .config import ModelCapability, plugin_config
from .data_source import get_image_model_candidates
from .providers import ImageResponseError, ProviderError, ProviderName, generate_images, image_tool_options
from .providers.openai_image_limits import aligned_ratio_size, size_error, uses_official_image_api
from .schemas import Completion, Message

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .config import ModelConfig
    from .schemas import ImageContent, Usage


SUPPORTED_FORMATS = frozenset({"gif", "png", "jpeg", "webp"})
HD_SIZE = "2880x2880"
DEFAULT_SHORT_EDGE = 1024
_PIXELS = r"[1-9][0-9]{0,4}"
SIZE_PATTERN = re.compile(rf"{_PIXELS}x{_PIXELS}")

# Interpret output requirements, not subjects, in the direct drawing command.
_QUOTED_TEXT = re.compile(r'“[^”]*”|「[^」]*」|『[^』]*』|"[^"]*"')
_NON_OUTPUT_PREFIX = re.compile(
    r"(?:不要|不需要|不用|无需|不是|别|写着|写上|印上|(?:时间|时刻)(?:为|是)?\s*[：:]?|(?<![A-Za-z])(?:no|not|without))"
    r"\s*(?:用|做|生成|画|输出|use\s+|make\s+)?\s*$",
    re.IGNORECASE,
)
_FORMAT_HINT = re.compile(r"(?<![A-Za-z0-9])(?:GIF|PNG|JPE?G|WebP)(?![A-Za-z0-9])", re.IGNORECASE)
_ANIMATION_HINT = re.compile(
    r"动图|动态(?!\s*的?\s*(?:感|光影|姿势|构图|镜头|视角|效果|文字|模糊|线条))|\banimated\b",
    re.IGNORECASE,
)
_HD_HINT = re.compile(r"高清|(?<![A-Za-z0-9])HD(?![A-Za-z0-9])", re.IGNORECASE)
_SIZE_PAIR = re.compile(rf"(?<![0-9.+-])({_PIXELS})\s*(?:[x×*＊]|乘以?)\s*({_PIXELS})(?![0-9.])", re.IGNORECASE)
_SQUARE_SIZE = re.compile(
    rf"(?<![0-9.+-])({_PIXELS})\s*(?:px|像素)?\s*(?:的\s*)?(?:正?方形|见方|square\b)", re.IGNORECASE
)
_DIMENSION = re.compile(rf"(宽度?|高度?|\bwidth\b|\bheight\b)\s*[:：=为是]?\s*({_PIXELS})(?![0-9.])", re.IGNORECASE)
_ASPECT_RATIO = re.compile(rf"(?<![0-9.:：∶+-])({_PIXELS})\s*[：:∶]\s*({_PIXELS})(?![0-9.:：∶])")
_FRAME_HINT = re.compile(r"(?<![0-9.+-])([0-9]{1,3})\s*(?:帧|frames?\b)", re.IGNORECASE)
_FRAME_ERROR = "官方 GIF 帧数必须是 2 至 16 之间的整数"


def _output_matches(pattern: re.Pattern[str], prompt: str) -> Iterator[re.Match[str]]:
    for match in pattern.finditer(prompt):
        if not _NON_OUTPUT_PREFIX.search(prompt[max(0, match.start() - 24) : match.start()]):
            yield match


def _infer_format(prompt: str) -> str:
    formats = {match.group().lower().replace("jpg", "jpeg") for match in _output_matches(_FORMAT_HINT, prompt)}
    if next(_output_matches(_ANIMATION_HINT, prompt), None):
        formats.add("gif")
    if len(formats) > 1:
        raise ProviderError("图片描述包含多个格式要求，请用 --format 明确指定")
    return next(iter(formats), "")


def _infer_size(prompt: str) -> str:
    sizes = {f"{match[1]}x{match[2]}" for match in _output_matches(_SIZE_PAIR, prompt)}
    sizes.update(f"{match[1]}x{match[1]}" for match in _output_matches(_SQUARE_SIZE, prompt))
    width, height = set(), set()
    for match in _output_matches(_DIMENSION, prompt):
        (width if match[1].lower() in {"宽", "宽度", "width"} else height).add(match[2])
    if width and height:
        if len(width) != 1 or len(height) != 1:
            raise ProviderError("图片描述包含多个尺寸要求，请用 --size 明确指定")
        sizes.add(f"{next(iter(width))}x{next(iter(height))}")
    if len(sizes) > 1:
        raise ProviderError("图片描述包含多个尺寸要求，请用 --size 明确指定")
    return next(iter(sizes), "")


def _infer_ratio(prompt: str) -> tuple[int, int] | None:
    ratios = set()
    for match in _output_matches(_ASPECT_RATIO, prompt):
        width, height = int(match[1]), int(match[2])
        divisor = gcd(width, height)
        ratios.add((width // divisor, height // divisor))
    if len(ratios) > 1:
        raise ProviderError("图片描述包含多个宽高比要求，请用 --size 明确指定")
    return next(iter(ratios), None)


def _size_at_short_edge(ratio: tuple[int, int], pixels: int) -> str:
    short = min(ratio)
    width, height = ((part * pixels + short // 2) // short for part in ratio)
    return f"{width}x{height}"


def _uses_official_geometry(model: ModelConfig) -> bool:
    return model.provider == ProviderName.OPENAI_IMAGES and uses_official_image_api(model.base_url, model.model)


@dataclass(frozen=True)
class ImageRequirements:
    output_format: str = ""
    size: str = ""
    aspect_ratio: tuple[int, int] | None = None
    ratio_short_edge: int | None = None
    frame_count: int | None = None
    hd: bool = False

    @classmethod
    def from_options(
        cls, output_format: str = "", size: str = "", *, hd: bool = False, frames: str = ""
    ) -> ImageRequirements:
        output_format = output_format.lower()
        size = size.lower()
        if output_format and output_format not in SUPPORTED_FORMATS:
            raise ProviderError("--format 仅支持 gif、png、jpeg、webp")
        if size and size != "auto" and not SIZE_PATTERN.fullmatch(size):
            raise ProviderError("--size 应为 WIDTHxHEIGHT，例如 1024x1024，或 auto")
        frame_count = None
        if frames:
            if output_format and output_format != "gif":
                raise ProviderError("--frames 仅适用于 GIF")
            if not re.fullmatch(r"[0-9]{1,2}", frames) or not 2 <= int(frames) <= 16:
                raise ProviderError(_FRAME_ERROR)
            frame_count = int(frames)
            output_format = "gif"
        if hd and size and size != HD_SIZE and output_format != "gif":
            raise ProviderError(f"--hd 固定为 {HD_SIZE}，与 --size {size} 冲突")
        return cls(output_format, size, frame_count=frame_count, hd=hd)

    def with_prompt(self, prompt: str) -> ImageRequirements:
        """Fill only fields that were not explicitly specified by flags."""
        hints = _QUOTED_TEXT.sub(" ", prompt)
        output_format = self.output_format or _infer_format(hints)
        frame_count = self.frame_count
        if frame_count is None and output_format == "gif":
            counts = {int(match[1]) for match in _output_matches(_FRAME_HINT, hints)}
            if len(counts) > 1:
                raise ProviderError("图片描述包含多个 GIF 帧数，请用 --frames 明确指定")
            frame_count = next(iter(counts), None)
            if frame_count is not None and not 2 <= frame_count <= 16:
                raise ProviderError(_FRAME_ERROR)
        requirements = replace(self, output_format=output_format, frame_count=frame_count)
        if self.size:
            return requirements
        if self.hd and output_format != "gif":
            return replace(requirements, size=HD_SIZE)
        size, ratio = _infer_size(hints), _infer_ratio(hints)
        if size:
            if ratio:
                width, height = map(int, size.split("x"))
                if width * ratio[1] != height * ratio[0]:
                    raise ProviderError(f"图片描述的宽高比 {ratio[0]}:{ratio[1]} 与尺寸 {size} 冲突")
            return replace(requirements, size=size)
        if self.hd or next(_output_matches(_HD_HINT, hints), None):
            if output_format == "gif":
                return replace(requirements, aspect_ratio=ratio, hd=True)
            if not ratio:
                return replace(requirements, size=HD_SIZE)
            return replace(requirements, aspect_ratio=ratio, ratio_short_edge=int(HD_SIZE.split("x")[0]))
        return replace(requirements, aspect_ratio=ratio)

    def size_for(self, model: ModelConfig) -> str:
        if self.size:
            return self.size
        defaults = image_tool_options(model)
        default_size = defaults.get("size")
        if not isinstance(default_size, str):
            default_size = ""
        output_format = self.output_format or defaults.get("output_format") or "png"
        if self.hd:
            if _uses_official_geometry(model) and output_format == "gif":
                return "auto"
            return _size_at_short_edge(self.aspect_ratio, int(HD_SIZE.split("x")[0])) if self.aspect_ratio else HD_SIZE
        format_sizes = model.image_sizes_by_format.get(output_format, set())
        short_edge = DEFAULT_SHORT_EDGE
        if SIZE_PATTERN.fullmatch(default_size.lower()):
            short_edge = min(map(int, default_size.lower().split("x")))
        if _uses_official_geometry(model) and output_format == "gif":
            presets = model.image_gif_size_presets or format_sizes
            restriction = model.image_sizes_by_format.get("gif", model.image_sizes or None)
            if restriction is not None:
                presets = presets & restriction
            if not self.aspect_ratio and default_size in presets:
                return default_size
            ratio = self.aspect_ratio or (1, 1)
            matching = []
            for value in sorted(presets):
                width, height = map(int, value.split("x"))
                if width * ratio[1] == height * ratio[0]:
                    edge = min(width, height)
                    matching.append(((abs(edge - short_edge), -edge), value))
            if matching:
                return min(matching)[1]
        if not self.aspect_ratio:
            if len(format_sizes) == 1 and default_size not in format_sizes:
                return next(iter(format_sizes))
            return ""
        short_edge = self.ratio_short_edge or short_edge
        if _uses_official_geometry(model):
            return aligned_ratio_size(
                self.aspect_ratio, short_edge, fit_hd=self.ratio_short_edge is not None and output_format != "gif"
            )
        return _size_at_short_edge(self.aspect_ratio, short_edge)

    def unsupported(self, model: ModelConfig, *, use_context: bool = False, references: bool = False) -> str:
        if ModelCapability.IMAGE_GENERATION not in model.capabilities:
            return "未声明 image_generation 能力，不能生成图片"
        official = _uses_official_geometry(model)
        if model.provider != ProviderName.OPENAI_RESPONSES:
            if official and use_context:
                return "不支持 -c 多轮续画，请回复具体图片改图"
            if not official and (use_context or references):
                return "只支持生成，不支持参考图或多轮续画"
        elif references and ModelCapability.VISION not in model.capabilities:
            return "未声明 vision 能力，不能使用参考图"
        defaults = image_tool_options(model)
        output_format = self.output_format or defaults.get("output_format") or "png"
        if output_format == "gif" and model.provider != ProviderName.OPENAI_IMAGES:
            return "此接口不支持动态 GIF"
        if self.frame_count is not None and not official:
            return "指定 GIF 帧数仅支持官方 Images 直连"
        official_static_format = (
            official and not model.image_output_formats and output_format in {"png", "jpeg", "webp"}
        )
        if (
            self.output_format
            and self.output_format not in model.image_output_formats
            and self.output_format != defaults.get("output_format")
            and not official_static_format
        ):
            return f"未声明支持 {self.output_format} 格式"
        size = self.size_for(model)
        if size == "auto" and not official:
            return "显式 --size auto 仅支持官方 Images 直连"
        if size and size != "auto" and not SIZE_PATTERN.fullmatch(size):
            return f"换算出的尺寸 {size} 超出允许范围"
        effective_size = size or defaults.get("size") or "auto"
        format_sizes = model.image_sizes_by_format.get(output_format)
        if official and effective_size != "auto":
            if not isinstance(effective_size, str) or not SIZE_PATTERN.fullmatch(effective_size):
                return "官方 Images 尺寸须为 WIDTHxHEIGHT 或 auto"
            if output_format != "gif" and self.aspect_ratio and max(self.aspect_ratio) > 3 * min(self.aspect_ratio):
                return "官方 Images 宽高比必须在 1:3 至 3:1 之间"
            if error := size_error(*map(int, effective_size.split("x")), animated=output_format == "gif"):
                return error
        if format_sizes is not None:
            if not isinstance(effective_size, str) or effective_size not in format_sizes:
                available = "、".join(sorted(format_sizes)) or "无"
                return f"{output_format} 未声明支持 {effective_size}，已配置尺寸：{available}"
        elif size and size not in model.image_sizes and size != defaults.get("size"):
            if not (official and not model.image_sizes):
                return f"未声明支持 {size} 尺寸"
        if official and output_format == "gif":
            frames = self.frame_count if self.frame_count is not None else model.extra_body.get("frame_count")
            if frames is not None and (not isinstance(frames, int) or not 2 <= frames <= 16):
                return _FRAME_ERROR
            duration = model.extra_body.get("frame_duration_ms")
            if duration is not None and (not isinstance(duration, int) or not 20 <= duration <= 2000):
                return "官方 GIF 每帧时长必须是 20 至 2000 毫秒的整数"
            if (
                model.extra_body.get("stream")
                or model.extra_body.get("partial_images")
                or model.extra_body.get("output_compression") is not None
            ):
                return "官方 GIF 不支持流式、部分图片或自定义压缩"
        if not model.base_url:
            return "未配置 base_url，且未设置 LLM__BASE_URL"
        return ""

    def apply(self, model: ModelConfig) -> ModelConfig:
        overrides = {
            key: value
            for key, value in (
                ("output_format", self.output_format),
                ("size", self.size_for(model)),
                ("frame_count", self.frame_count),
            )
            if value
        }
        return model.model_copy(update={"extra_body": {**model.extra_body, **overrides}}) if overrides else model

    def verify(self, images: list[ImageContent], model: ModelConfig) -> str:
        output_format = self.output_format
        if not output_format and image_tool_options(model).get("output_format") == "gif":
            output_format = "gif"
        size = self.size_for(model)
        if not output_format and not size:
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
            except (OSError, ValueError, Image.DecompressionBombError) as e:
                raise ProviderError(f"第 {number} 张图片无法核验格式或尺寸") from e
            if output_format and output_format != actual_format:
                raise ProviderError(f"第 {number} 张图片要求 {output_format}，服务返回 {actual_format}")
            if size and size != "auto" and size != actual_size:
                raise ProviderError(f"第 {number} 张图片要求 {size}，服务返回 {actual_size}")
            if actual_format == "gif" and frames < 2:
                raise ProviderError(f"第 {number} 张图片要求多帧 GIF，服务返回 {frames} 帧")
            if actual_format == "gif" and _uses_official_geometry(model):
                if size == "auto" and self.aspect_ratio:
                    a, b = self.aspect_ratio
                    if width * b != height * a:
                        raise ProviderError(f"第 {number} 张图片要求宽高比 {a}:{b}，服务返回 {actual_size}")
                expected_frames = (
                    self.frame_count if self.frame_count is not None else model.extra_body.get("frame_count")
                )
                if expected_frames is not None and frames != expected_frames:
                    raise ProviderError(f"第 {number} 张图片要求 {expected_frames} 帧 GIF，服务返回 {frames} 帧")
            frames_text = f" / {frames} 帧" if actual_format == "gif" else ""
            details.append(f"{actual_format.upper()} {actual_size}{frames_text}")
        return "、".join(dict.fromkeys(details))


async def select_image_model(
    session_id: str,
    *,
    selected_name: str = "",
    requirements: ImageRequirements = ImageRequirements(),
    use_context: bool = False,
    references: bool = False,
) -> ModelConfig:
    enabled, candidates = await get_image_model_candidates(session_id)
    if selected_name:
        if selected_name not in enabled:
            raise ProviderError(f"本群未启用的模型：{selected_name}")
        candidates = [selected_name]
    if not candidates:
        raise ProviderError("本群未启用生图模型，请联系超级管理员启用并设置")
    reasons = []
    for name in candidates:
        model = plugin_config.resolve(name)
        reason = requirements.unsupported(model, use_context=use_context, references=references)
        if not reason:
            return model
        reasons.append(f"{name}：{reason}")
    ratio = requirements.aspect_ratio
    geometry = f"{ratio[0]}:{ratio[1]}" if ratio else requirements.size
    requested = " / ".join(filter(None, (requirements.output_format.upper(), geometry)))
    if requested:
        reasons.insert(0, f"要求 {requested}")
    raise ProviderError("本群没有满足绘图要求的模型（" + "；".join(reasons) + "）")


@dataclass
class ImageResult:
    model_name: str
    images: list[ImageContent]
    usage: Usage | None
    elapsed_seconds: float
    details: str = ""

    def summary(self) -> str:
        usage = self.usage.to_chinese() if self.usage is not None else "服务未返回用量"
        details = f" · {self.details}" if self.details else ""
        return f"生图模型：{self.model_name} · {len(self.images)} 张{details} · {self.elapsed_seconds:.1f}s · {usage}"


@dataclass(kw_only=True)
class ImageChatCompletion(Completion):
    """带有独立图片用量的聊天回复，不把图片 token 合并为聊天模型用量。"""

    image_result: ImageResult | None = None
    image_error: str = ""


@dataclass
class ImageTask:
    model: ModelConfig
    session_affinity: str
    use_context: bool = False
    requirements: ImageRequirements = field(default_factory=ImageRequirements)
    history: list[Message] = field(default_factory=list, init=False)
    can_continue: bool = field(default=True, init=False)

    async def run(self, prompt: str, images: list[ImageContent] | None = None) -> ImageResult:
        reason = self.requirements.unsupported(self.model, use_context=self.use_context, references=bool(images))
        if reason:
            raise ProviderError(f"生图模型 {self.model.name} {reason}")
        if not self.can_continue:
            raise ProviderError("生图服务没有返回可续画的图片记录；已停止多轮绘图，未重新生成")
        if not prompt.strip():
            raise ProviderError("请提供绘图描述")
        started_at = perf_counter()
        try:
            generated = await generate_images(
                self.requirements.apply(self.model),
                prompt,
                session_affinity=self.session_affinity,
                images=images,
                history=self.history,
            )
        except ImageResponseError as e:
            if e.usage is not None:
                logger.info("LLM 图片请求返回不可交付结果（模型={}，{}）", self.model.name, e.usage.to_chinese())
            raise
        result = ImageResult(self.model.name, generated.images, generated.usage, perf_counter() - started_at)
        logger.info("LLM 图片请求完成（{}）", result.summary())
        result.details = self.requirements.verify(generated.images, self.model)
        if self.use_context:
            if generated.continuation is not None:
                self.history.extend((Message.user(prompt, images), generated.continuation))
            else:
                self.can_continue = False
        return result

    def rollback(self) -> bool:
        if not self.history:
            return False
        del self.history[-2:]
        return True
