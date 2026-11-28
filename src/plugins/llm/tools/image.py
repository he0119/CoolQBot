"""聊天模型按需调用绘图时的一轮状态。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from nonebot.log import logger

from ..image_requirements import ImageRequirements
from ..image_service import select_image_task
from ..providers import ProviderError
from . import ToolContext, ToolResult, registry

if TYPE_CHECKING:
    from ..schemas import ImageContent, ImageResult

IMAGE_TOOL_NAME = "generate_image"


@dataclass(frozen=True)
class ImageToolOptions:
    model_name: str = ""
    requirements: ImageRequirements = field(default_factory=ImageRequirements)


@dataclass
class ImageToolTurn:
    session_id: str
    session_affinity: str
    options: ImageToolOptions
    attachments: list[ImageContent] | None = None
    attempted: bool = False
    result: ImageResult | None = None
    error: ProviderError | None = None

    async def run(self, prompt: str, *, use_reference: bool) -> ImageResult:
        if self.attempted:
            raise ProviderError("本轮绘图次数已用完，不会再次生成")
        # 在等待群配置或外部接口前占用本轮次数，防止并行重复出图。
        self.attempted = True
        try:
            references = self.attachments if use_reference else None
            if use_reference and not references:
                raise ProviderError("本轮没有可用于改图的参考图")
            requirements = self.options.requirements.with_prompt(prompt)
            task = await select_image_task(
                self.session_id, requirements, selected_name=self.options.model_name, references=bool(references)
            )
            self.result, _ = await task.run(prompt, session_affinity=self.session_affinity, images=references)
        except ProviderError as error:
            self.error = error
            raise
        return self.result


@dataclass(frozen=True, kw_only=True)
class ImageToolContext(ToolContext):
    image_turn: ImageToolTurn


@registry.register(
    IMAGE_TOOL_NAME,
    "按文字描述生成图片，或按用户要求编辑附件。每轮最多调用一次，成功图片会随回复发送给用户。",
    needs_context=True,
)
async def generate_image(prompt: str, use_reference: bool = False, *, context: ToolContext) -> ToolResult:
    """生成或编辑图片。

    Args:
        prompt: 图片描述，尽量写清主体、风格和构图
        use_reference: 仅在用户要求以本轮附件为参考或编辑附件时设为 true
    """
    if not isinstance(context, ImageToolContext):
        return ToolResult(text="错误：本轮未启用生图工具")
    try:
        result = await context.image_turn.run(prompt, use_reference=use_reference)
    except ProviderError as error:
        logger.warning("LLM 图片生成失败（错误={}）", error)
        return ToolResult(text=f"错误：生成图片失败：{error}")
    return ToolResult(
        text=f"使用生图模型 {result.model_name} 生成了 {len(result.images)} 张图片，将随回复发送给用户。",
        images=result.images,
    )
