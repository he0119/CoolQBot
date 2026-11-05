"""图片生成工具

模型通过函数调用触发，插件再用本群配置的生图模型调用 Image API，
生成的图片直接发送给用户，只把一句结果文本交回模型继续作答。
"""

from __future__ import annotations

from nonebot.log import logger

from ..config import plugin_config
from ..providers import ImagesProvider, ProviderError, ProviderName
from . import ToolContext, ToolResult, registry


@registry.register(
    "generate_image",
    "根据文字描述生成图片。用户要求画图、生成图片或修改图片时调用；生成结果会直接发送给用户。",
    needs_context=True,
)
async def generate_image(prompt: str, *, context: ToolContext) -> ToolResult:
    """生成图片

    Args:
        prompt: 图片描述，尽量写清主体、风格和构图
    """
    if not context.image_model_name:
        return ToolResult(text="错误：本群未启用生图模型，请联系管理员配置")
    try:
        model = plugin_config.get_model(context.image_model_name)
    except ValueError:
        return ToolResult(text=f"错误：生图模型 {context.image_model_name} 不再可用")
    if model.provider != ProviderName.OPENAI_IMAGES:
        return ToolResult(text=f"错误：生图模型 {model.name} 未使用 openai_images 接口，不能生成图片")
    provider = ImagesProvider(model, session_affinity=context.session_id)
    try:
        generated = await provider.generate(prompt)
    except ProviderError as e:
        logger.warning("LLM 图片生成失败（模型={}，错误={}）", model.name, e)
        return ToolResult(text=f"错误：生成图片失败：{e}")
    return ToolResult(
        text=f"已生成 {len(generated.images)} 张图片，图片已直接发送给用户。",
        images=generated.images,
    )
