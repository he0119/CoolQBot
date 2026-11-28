"""从绘图选项和用户描述中提取输出规格。"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from math import gcd
from typing import TYPE_CHECKING

from .providers.base import ProviderError

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["DEFAULT_SHORT_EDGE", "HD_SIZE", "SIZE_PATTERN", "ImageRequirements"]

HD_SIZE = "2880x2880"
DEFAULT_SHORT_EDGE = 1024
_SUPPORTED_FORMATS = frozenset({"gif", "png", "jpeg", "webp"})
_PIXELS = r"[1-9][0-9]{0,4}"
SIZE_PATTERN = re.compile(rf"{_PIXELS}x{_PIXELS}")

_QUOTED_TEXT = re.compile(
    r"“[^”]*”|‘[^’]*’|「[^」]*」|『[^』]*』|`+[^`]*`+"
    r'|"(?:\\.|[^"\\])*"'
    r"|(?<![A-Za-z0-9])'(?:\\.|[^'\\])*'(?![A-Za-z0-9])"
)
_CLAUSE_BREAK = re.compile(r"[,，；;。！？!?\n]|但是|不过|而是|(?<!不)但|\b(?:but|instead)\b", re.IGNORECASE)
_LITERAL_PREFIX = re.compile(
    r"(?:写[着上]|印[着上]|刻[着上]|标[着上]|显示(?:着|为)?|(?:时间|时刻)(?:为|是)?|"
    r"\b(?:reads?|says?|displaying|showing)\b)\s*[:：]?\s*$",
    re.IGNORECASE,
)
_FORMAT_HINT = re.compile(r"(?<![A-Za-z0-9])(?:GIF|PNG|JPE?G|WebP)(?![A-Za-z0-9])", re.IGNORECASE)
_ANIMATION_HINT = re.compile(
    r"动图|动态(?!\s*的?\s*(?:感|光影|姿势|构图|镜头|视角|效果|文字|模糊|线条))|\banimated\b",
    re.IGNORECASE,
)
_HD_HINT = re.compile(r"高清|(?<![A-Za-z0-9])HD(?![A-Za-z0-9])", re.IGNORECASE)
_NEGATED_REQUIREMENT = re.compile(
    r"(?:不要|不需要|不用|无需|不是|不必|不想|不(?:画|做|生成|输出|改)(?:成|为)?|避免|而非|"
    r"(?<![个特分识区辨])别|(?<![A-Za-z])(?:no|not|without|avoid|don['’]t|rather than)(?![A-Za-z]))"
    r"\s*(?:(?:把(?:它|(?:这|那)?张?图(?:片)?)|[画做改转](?:成|为)?|使用|用|生成|输出|导出|"
    r"\b(?:use|make|generate|output|render|export|draw)\b)\s*)*(?:一[张幅个]\s*|(?:an?|the)\s+)?"
    rf"(?=[0-9]|宽高比|长宽比|比例|尺寸|格式|帧数|[宽高](?:度)?\s*[0-9:：]|"
    rf"{_FORMAT_HINT.pattern}|{_ANIMATION_HINT.pattern}|{_HD_HINT.pattern}|\b(?:size|ratio|format|frame count)\b)",
    re.IGNORECASE,
)
_SIZE_PAIR = re.compile(rf"(?<![0-9.+-])({_PIXELS})\s*(?:[x×*＊]|乘以?)\s*({_PIXELS})(?![0-9.])", re.IGNORECASE)
_SQUARE_SIZE = re.compile(
    rf"(?<![0-9.+-])({_PIXELS})\s*(?:px|像素)?\s*(?:的\s*)?(?:正?方形|见方|square\b)", re.IGNORECASE
)
_DIMENSION = re.compile(rf"(宽度?|高度?|\bwidth\b|\bheight\b)\s*[:：=为是]?\s*({_PIXELS})(?![0-9.])", re.IGNORECASE)
_ASPECT_RATIO = re.compile(rf"(?<![0-9.:：∶+-])({_PIXELS})\s*[：:∶]\s*({_PIXELS})(?![0-9.:：∶])")
_CLOCK_TIME = re.compile(r"(?:[01]?[0-9]|2[0-3])\s*[:：]\s*[0-5][0-9]")
_CLOCK_SUFFIX = re.compile(r"\s*(?:的\s*)?(?:闹钟|时钟|钟表|手表|[ap]m\b)", re.IGNORECASE)
_RATIO_LABEL = re.compile(r"(?:宽高比|长宽比|比例|\bratio\b)\s*[:：=为是]?\s*$", re.IGNORECASE)
_FRAME_HINT = re.compile(r"(?<![0-9.+-])([0-9]{1,3})\s*(?:帧|frames?\b)", re.IGNORECASE)
_FRAME_COUNT_HINT = re.compile(
    r"(?:帧数|\bframe count\b)\s*(?:(?:改[为成]|设(?:置)?为|为|是|to)\s*|[:：=]\s*)?([0-9]{1,3})(?![0-9.])",
    re.IGNORECASE,
)
_FRAME_ERROR = "官方 GIF 帧数必须是 2 至 16 之间的整数"


def _output_text(prompt: str) -> str:
    # 否定的规格作用到分隔符或转折词之前。例如，「不要做成 GIF 动图，但输出 PNG」。
    clauses = _CLAUSE_BREAK.split(_QUOTED_TEXT.sub(" ", prompt))
    return "。".join(_NEGATED_REQUIREMENT.split(clause, maxsplit=1)[0] for clause in clauses)


def _output_matches(pattern: re.Pattern[str], prompt: str) -> Iterator[re.Match[str]]:
    for match in pattern.finditer(prompt):
        prefix = prompt[max(0, match.start() - 24) : match.start()]
        if not _LITERAL_PREFIX.search(prefix):
            yield match


def _infer_format(prompt: str) -> str:
    formats = {match.group().lower().replace("jpg", "jpeg") for match in _output_matches(_FORMAT_HINT, prompt)}
    if any(_output_matches(_ANIMATION_HINT, prompt)):
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
        if (
            _CLOCK_TIME.fullmatch(match[0])
            and _CLOCK_SUFFIX.match(prompt, match.end())
            and not _RATIO_LABEL.search(prompt, 0, match.start())
        ):
            continue
        width, height = int(match[1]), int(match[2])
        divisor = gcd(width, height)
        ratios.add((width // divisor, height // divisor))
    if len(ratios) > 1:
        raise ProviderError("图片描述包含多个宽高比要求，请用 --size 明确指定")
    return next(iter(ratios), None)


def _infer_geometry(prompt: str, *, allow_size: bool = True) -> tuple[str, tuple[int, int] | None]:
    size = _infer_size(prompt) if allow_size else ""
    ratio = _infer_ratio(prompt)
    if size and ratio:
        width, height = map(int, size.split("x"))
        if width * ratio[1] != height * ratio[0]:
            raise ProviderError(f"图片描述的宽高比 {ratio[0]}:{ratio[1]} 与尺寸 {size} 冲突")
    return size, ratio


def _infer_frame_count(prompt: str) -> int | None:
    counts = {
        int(match[1]) for pattern in (_FRAME_HINT, _FRAME_COUNT_HINT) for match in _output_matches(pattern, prompt)
    }
    if len(counts) > 1:
        raise ProviderError("图片描述包含多个 GIF 帧数，请用 --frames 明确指定")
    count = next(iter(counts), None)
    if count is not None and not 2 <= count <= 16:
        raise ProviderError(_FRAME_ERROR)
    return count


def _validate_hd_size(size: str, output_format: str, *, hd: bool) -> None:
    if hd and size and size != HD_SIZE and output_format != "gif":
        raise ProviderError(f"--hd 固定为 {HD_SIZE}，与 --size {size} 冲突")


@dataclass(frozen=True)
class ImageRequirements:
    """用户提出的规格，绘图层据此决定实际发送的尺寸。"""

    output_format: str = ""
    size: str = ""
    aspect_ratio: tuple[int, int] | None = None
    frame_count: int | None = None
    hd: bool = False

    @classmethod
    def from_options(
        cls, output_format: str = "", size: str = "", *, hd: bool = False, frames: str = ""
    ) -> ImageRequirements:
        """解析选项，缺少输出格式时由 with_prompt 完成高清尺寸校验。"""
        output_format = output_format.lower()
        size = size.lower()
        if output_format and output_format not in _SUPPORTED_FORMATS:
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
        if output_format:
            _validate_hd_size(size, output_format, hd=hd)
        return cls(output_format=output_format, size=size, frame_count=frame_count, hd=hd)

    def with_prompt(self, prompt: str) -> ImageRequirements:
        """按描述补齐首轮规格，命令选项优先。"""
        hints = _output_text(prompt)
        output_format = self.output_format or _infer_format(hints)
        _validate_hd_size(self.size, output_format, hd=self.hd)
        frame_count = self.frame_count if output_format == "gif" else None
        if frame_count is None and output_format == "gif":
            frame_count = _infer_frame_count(hints)
        size, ratio = self.size, self.aspect_ratio
        if not size or size == "auto":
            allow_size = not size and (not self.hd or output_format == "gif")
            inferred_size, inferred_ratio = _infer_geometry(hints, allow_size=allow_size)
            if inferred_size:
                size, ratio = inferred_size, None
            elif inferred_ratio is not None:
                ratio = inferred_ratio
        return replace(
            self,
            output_format=output_format,
            size=size,
            aspect_ratio=ratio,
            frame_count=frame_count,
            hd=self.hd or (not size and any(_output_matches(_HD_HINT, hints))),
        )

    def follow_up(self, prompt: str) -> ImageRequirements:
        """用本轮描述更新输出规格，沿用本轮未提及的要求。"""
        hints = _output_text(prompt)
        output_format = _infer_format(hints) or self.output_format
        frame_count = (_infer_frame_count(hints) or self.frame_count) if output_format == "gif" else None
        size, ratio = _infer_geometry(hints)
        hd = self.hd
        if size:
            ratio, hd = None, False
        elif ratio is not None:
            size = "auto" if self.size == "auto" else ""
        else:
            size, ratio = self.size, self.aspect_ratio
        if not size:
            hd = hd or any(_output_matches(_HD_HINT, hints))
        elif self.output_format == "gif" and output_format != "gif" and size != HD_SIZE:
            # 合用高清与该尺寸只在 GIF 中有效，切成静态格式时沿用尺寸。
            hd = False
        return replace(self, output_format=output_format, size=size, aspect_ratio=ratio, frame_count=frame_count, hd=hd)
