"""官方 GPT Image 型号的改图、动画与像素限制。"""

_OFFICIAL_URL = "https://api.openai.com/v1"
_GIF_MODELS = frozenset({"gpt-image-2.6-sunburst", "gpt-image-2.6-flare"})
_VARIABLE_SIZE_MODELS = _GIF_MODELS | {
    "gpt-image-2",
    "gpt-image-2-2026-04-21",
    "gpt-image-2.5-sunburst",
    "gpt-image-2.5-sunburst-2026-09-08",
    "gpt-image-2.5-flare",
    "gpt-image-2.5-flare-2026-09-08",
}
_EDIT_MODELS = _VARIABLE_SIZE_MODELS | {"gpt-image-1.5", "gpt-image-1-mini"}
MAX_EDGE = 3840
MIN_PIXELS = 655_360
MAX_PIXELS = 8_294_400
ALIGNMENT = 16


def is_official_endpoint(base_url: str) -> bool:
    return base_url.rstrip("/") == _OFFICIAL_URL


def supports_official_image_edits(base_url: str, model_id: str) -> bool:
    return is_official_endpoint(base_url) and model_id in _EDIT_MODELS


def uses_official_image_api(base_url: str, model_id: str) -> bool:
    """该直连接入适用可变像素规则。"""
    return is_official_endpoint(base_url) and model_id in _VARIABLE_SIZE_MODELS


def supports_official_gif(base_url: str, model_id: str) -> bool:
    return is_official_endpoint(base_url) and model_id in _GIF_MODELS


def size_error(width: int, height: int, *, animated: bool = False) -> str:
    if max(width, height) > MAX_EDGE:
        return f"官方 Images 单边最多 {MAX_EDGE} 像素"
    if width % ALIGNMENT or height % ALIGNMENT:
        return f"官方 Images 宽高都必须是 {ALIGNMENT} 的倍数"
    # For GIF, the still-image pixel budget applies to the generated sheet, not each frame.
    # Only project-verified GIF frame sizes are allowed by the caller.
    if animated:
        return ""
    if max(width, height) > 3 * min(width, height):
        return "官方 Images 宽高比必须在 1:3 至 3:1 之间"
    if not MIN_PIXELS <= width * height <= MAX_PIXELS:
        return f"官方 Images 总像素必须在 {MIN_PIXELS} 至 {MAX_PIXELS} 之间"
    return ""


def aligned_ratio_size(ratio: tuple[int, int], short_edge: int, *, fit_hd: bool) -> str:
    """Align inferred pixels only; for the HD preset fit the largest legal canvas below its target."""
    short_part = min(ratio)
    step = ALIGNMENT
    target = max(step, (short_edge + step // 2) // step * step)

    def dimensions(edge: int) -> tuple[int, int]:
        unit = short_part * step
        width, height = (max(step, (part * edge + unit // 2) // unit * step) for part in ratio)
        return width, height

    width, height = dimensions(target)
    if fit_hd and max(ratio) <= 3 * short_part:
        for edge in range(min(target, MAX_EDGE), 0, -step):
            candidate = dimensions(edge)
            if not size_error(*candidate):
                width, height = candidate
                break
    return f"{width}x{height}"
