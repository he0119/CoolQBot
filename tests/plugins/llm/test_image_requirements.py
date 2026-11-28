from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from src.plugins.llm.image_requirements import ImageRequirements


@pytest.fixture
def requirements_type() -> type[ImageRequirements]:
    from src.plugins.llm.image_requirements import ImageRequirements

    return ImageRequirements


@pytest.mark.parametrize(
    ("prompt", "output_format", "size"),
    [
        ("画一张1024方形的魔理沙简笔动态头像", "gif", "1024x1024"),
        ("设计一张128像素见方的动态贴纸", "gif", "128x128"),
        ("渲染一张 640 × 480 的 WebP 横幅", "webp", "640x480"),
        ("导出 PNG，宽320像素、高240像素的宣传图", "png", "320x240"),
        ("Make an animated icon, 96px square", "gif", "96x96"),
        ("画一张4:3，尺寸960×720的JPG横幅", "jpeg", "960x720"),
        ("Make a cat without a hat in PNG", "png", ""),
    ],
)
def test_infers_legacy_formats_and_sizes(requirements_type: type[ImageRequirements], prompt, output_format, size):
    assert requirements_type().with_prompt(prompt) == requirements_type(output_format=output_format, size=size)


@pytest.mark.parametrize(
    "prompt",
    [
        "画一个显示 12:30 的闹钟",
        "画一个时间为 12:30 的闹钟",
        "画一个 12:30 的闹钟",
        "画海报，不要画成 GIF",
        "不要画成 12 帧的 GIF 动图",
        "Make an icon, not a 12 frame animated GIF",
        "画一张印着「12 帧 16:9 的高清 GIF」的海报",
        "画一张写有 '960x960 PNG' 的牌子",
    ],
)
def test_ignores_subject_and_excluded_requirements(requirements_type: type[ImageRequirements], prompt):
    assert requirements_type().with_prompt(prompt) == requirements_type()


def test_recognizes_affirmed_requirements_next_to_negation_or_clock(requirements_type: type[ImageRequirements]):
    prompt = "画一个显示 12:30 的闹钟，画面比例 16:9，不要画成 GIF 动图而是输出高清 PNG"
    assert requirements_type().with_prompt(prompt) == requirements_type(
        output_format="png", aspect_ratio=(16, 9), hd=True
    )


def test_recognizes_normalized_ratios_and_hd_without_fixed_pixels(requirements_type: type[ImageRequirements]):
    assert requirements_type().with_prompt("画一张32:18（16:9）的高清GIF头像") == requirements_type(
        output_format="gif", aspect_ratio=(16, 9), hd=True
    )


def test_explicit_ratio_can_match_a_clock_time(requirements_type: type[ImageRequirements]):
    assert requirements_type().with_prompt("画一张宽高比 12:30 的闹钟插画") == requirements_type(aspect_ratio=(2, 5))


def test_options_override_description(requirements_type: type[ImageRequirements]):
    options = requirements_type.from_options("JPEG", "40X30")
    assert options.with_prompt("9:16 或 4:3 的 128 方形 GIF 动图") == requirements_type(
        output_format="jpeg", size="40x30"
    )
    options = requirements_type.from_options(frames="12")
    assert options.with_prompt("20 帧或 10 帧的 PNG 动图") == requirements_type(output_format="gif", frame_count=12)


def test_auto_size_preserves_ratio_and_overrides_described_pixels(requirements_type: type[ImageRequirements]):
    options = requirements_type.from_options(size="AUTO")
    assert options.with_prompt("12 帧 16:9 的 960x960 GIF") == requirements_type(
        output_format="gif", size="auto", aspect_ratio=(16, 9), frame_count=12
    )


def test_static_pixels_take_precedence_over_described_hd(requirements_type: type[ImageRequirements]):
    assert requirements_type().with_prompt("输出 1280x960 高清 PNG") == requirements_type(
        output_format="png", size="1280x960"
    )
    assert requirements_type.from_options(size="1280x960").with_prompt("输出高清 PNG") == requirements_type(
        output_format="png", size="1280x960"
    )
    assert requirements_type.from_options(hd=True).with_prompt("输出 1280x960 的 PNG") == requirements_type(
        output_format="png", hd=True
    )


def test_hd_size_conflict_depends_on_effective_format(requirements_type: type[ImageRequirements]):
    from src.plugins.llm.providers import ProviderError

    options = requirements_type.from_options(size="960x960", hd=True)
    assert options.with_prompt("画一张 12 帧的 GIF 动图") == requirements_type(
        output_format="gif", size="960x960", frame_count=12, hd=True
    )
    with pytest.raises(ProviderError, match="--hd 固定为 2880x2880，与 --size 960x960 冲突"):
        options.with_prompt("不要画成 GIF，输出 PNG")
    with pytest.raises(ProviderError, match="--hd 固定为 2880x2880，与 --size 960x960 冲突"):
        requirements_type.from_options("png", "960x960", hd=True)


@pytest.mark.parametrize(
    ("prompt", "error"),
    [
        ("输出 PNG 和 JPEG 的头像", "图片描述包含多个格式要求，请用 --format 明确指定"),
        ("尺寸 512x512 或 1024x1024 的猫", "图片描述包含多个尺寸要求，请用 --size 明确指定"),
        ("画一张16:9或4:3的头像", "图片描述包含多个宽高比要求，请用 --size 明确指定"),
        ("画一张16:9的960x720头像", "图片描述的宽高比 16:9 与尺寸 960x720 冲突"),
        ("画一张17帧的GIF", "官方 GIF 帧数必须是 2 至 16 之间的整数"),
        ("画一张 8 帧或 12 帧 GIF", "图片描述包含多个 GIF 帧数，请用 --frames 明确指定"),
    ],
)
def test_prompt_reports_compatibility_errors(requirements_type: type[ImageRequirements], prompt, error):
    from src.plugins.llm.providers import ProviderError

    with pytest.raises(ProviderError, match=error):
        requirements_type().with_prompt(prompt)


@pytest.mark.parametrize(
    ("options", "error"),
    [
        ({"output_format": "tiff"}, "--format 仅支持 gif、png、jpeg、webp"),
        ({"size": "large"}, "--size 应为 WIDTHxHEIGHT，例如 1024x1024，或 auto"),
        ({"frames": "1"}, "官方 GIF 帧数必须是 2 至 16 之间的整数"),
        ({"frames": "8", "output_format": "png"}, "--frames 仅适用于 GIF"),
    ],
)
def test_options_report_compatibility_errors(requirements_type: type[ImageRequirements], options, error):
    from src.plugins.llm.providers import ProviderError

    with pytest.raises(ProviderError, match=error):
        requirements_type.from_options(**options)


def test_follow_up_replaces_geometry_and_preserves_unmentioned_fields(requirements_type: type[ImageRequirements]):
    initial = requirements_type.from_options("png", "2880x2880", hd=True)
    assert initial.follow_up("只把背景换成蓝色") == initial
    wide = initial.follow_up("改用 16:9 比例")
    assert wide == requirements_type(output_format="png", aspect_ratio=(16, 9), hd=True)
    assert wide.follow_up("改成 960x720 像素的高清图") == requirements_type(output_format="png", size="960x720")
    auto = requirements_type(output_format="gif", size="auto", aspect_ratio=(16, 9))
    assert auto.follow_up("改用 4:3 比例") == requirements_type(output_format="gif", size="auto", aspect_ratio=(4, 3))
    assert initial.size == "2880x2880"


def test_follow_up_can_update_inherited_gif_frames_and_switch_to_static(requirements_type: type[ImageRequirements]):
    initial = requirements_type.from_options(size="960x960", frames="8").with_prompt("画一只猫")
    assert initial.follow_up("不要改成 12 帧，只换个背景") == initial
    longer = initial.follow_up("改成 12 帧，背景换成蓝色")
    assert longer == requirements_type(output_format="gif", size="960x960", frame_count=12)
    assert initial.follow_up("帧数改为 12") == longer
    assert initial.follow_up("set frame count to 12") == longer
    static = longer.follow_up("这次改成 PNG")
    assert static == requirements_type(output_format="png", size="960x960")
    assert static.follow_up("背景加上 12 帧动画的文字") == static
    assert static.follow_up("改成 10 帧的 GIF") == requirements_type(
        output_format="gif", size="960x960", frame_count=10
    )


def test_follow_up_clears_hd_when_fixed_pixels_are_incompatible_with_static(requirements_type: type[ImageRequirements]):
    initial = requirements_type.from_options(size="960x960", hd=True, frames="12")
    assert initial.follow_up("把猫换成狐狸") == initial
    assert initial.follow_up("这次改成 PNG") == requirements_type(output_format="png", size="960x960")


def test_follow_up_rejects_conflicts_in_the_current_turn(requirements_type: type[ImageRequirements]):
    from src.plugins.llm.providers import ProviderError

    initial = requirements_type(output_format="gif", size="960x960", frame_count=8)
    with pytest.raises(ProviderError, match="图片描述的宽高比 16:9 与尺寸 960x720 冲突"):
        initial.follow_up("改成 16:9，尺寸用 960x720")
    with pytest.raises(ProviderError, match="官方 GIF 帧数必须是 2 至 16 之间的整数"):
        initial.follow_up("改成 17 帧")
