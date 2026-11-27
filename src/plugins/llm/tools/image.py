"""仅在显式开启时，下发给聊天模型的图片工具。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from nonebot.log import logger

from ..image_service import ImageResult, ImageTask
from ..providers import ProviderError
from . import ToolContext, ToolResult, registry

if TYPE_CHECKING:
    from ..schemas import ImageContent

IMAGE_TOOL_NAME = "generate_image"


@dataclass
class ImageToolTurn:
    task: ImageTask
    references: list[ImageContent] | None = None
    attempted: bool = False
    result: ImageResult | None = None
    error: str = ""

    async def run(self, prompt: str) -> ImageResult:
        # 先占用预算再等待，同行并行调用和失败后的再次调用都不得再次发请求。
        if self.attempted:
            raise ProviderError("本轮绘图次数已用完，不会再次生成")
        self.attempted = True
        try:
            self.result = await self.task.run(prompt, self.references)
        except ProviderError as e:
            self.error = str(e)
            raise
        return self.result


@dataclass(frozen=True)
class ImageToolContext(ToolContext):
    image_turn: ImageToolTurn | None = None


@registry.register(
    IMAGE_TOOL_NAME,
    "根据文字描述生成图片；每轮最多调用一次，成功图片会随回复发送给用户。",
    needs_context=True,
)
async def generate_image(prompt: str, *, context: ToolContext) -> ToolResult:
    """生成图片。

    Args:
        prompt: 图片描述，尽量写清主体、风格和构图
    """
    model = context.image_model
    if model is None:
        return ToolResult(text="错误：本群未启用生图模型，请联系管理员配置")
    turn = context.image_turn if isinstance(context, ImageToolContext) else None
    if turn is None:
        turn = ImageToolTurn(ImageTask(model, context.session_id))
    try:
        result = await turn.run(prompt)
    except ProviderError as e:
        logger.warning("LLM 图片生成失败（模型={}，错误={}）", model.name, e)
        return ToolResult(text=f"错误：生成图片失败：{e}")
    return ToolResult(
        text=f"使用生图模型 {result.model_name} 生成了 {len(result.images)} 张图片，将随回复发送给用户。",
        images=result.images,
    )
