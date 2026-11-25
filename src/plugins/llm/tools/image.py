"""图片生成工具

模型通过函数调用触发，插件再用本群配置的生图模型生成图片，
生成的图片直接发送给用户，只把一句结果文本交回模型继续作答。
"""

from __future__ import annotations

from nonebot.log import logger

from ..config import ModelCapability
from ..providers import ProviderError, generate_images
from . import ToolContext, ToolResult, registry

IMAGE_TOOL_NAME = "generate_image"
"""生图工具名；生图会产生费用，只在用户显式要求时下发"""


@registry.register(
    IMAGE_TOOL_NAME,
    "根据文字描述生成图片。用户要求画图、生成图片或修改图片时调用；生成结果会直接发送给用户。",
    needs_context=True,
)
async def generate_image(prompt: str, *, context: ToolContext) -> ToolResult:
    """生成图片

    Args:
        prompt: 图片描述，尽量写清主体、风格和构图
    """
    model = context.image_model
    if model is None:
        return ToolResult(text="错误：本群未启用生图模型，请联系管理员配置")
    if ModelCapability.IMAGE_GENERATION not in model.capabilities:
        return ToolResult(text=f"错误：模型 {model.name} 未声明 image_generation 能力，不能生成图片")
    try:
        generated = await generate_images(model, prompt, session_affinity=context.session_id)
    except ProviderError as e:
        logger.warning("LLM 图片生成失败（模型={}，错误={}）", model.name, e)
        return ToolResult(text=f"错误：生成图片失败：{e}")
    return ToolResult(
        text=f"已生成 {len(generated.images)} 张图片，图片已直接发送给用户。",
        images=generated.images,
    )
