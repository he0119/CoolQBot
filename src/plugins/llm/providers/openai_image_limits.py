"""Published pixel limits of GPT-Image-2.6 on the official OpenAI Images API."""

MODELS = frozenset({"gpt-image-2.6-sunburst", "gpt-image-2.6-flare"})
MAX_EDGE = 3840
MIN_PIXELS = 655_360
MAX_PIXELS = 8_294_400
ALIGNMENT = 16


def uses_official_image_api(base_url: str, model_id: str) -> bool:
    return base_url.rstrip("/") == "https://api.openai.com/v1" and model_id in MODELS


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
