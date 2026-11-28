"""直接绘图命令和同一生图模型的多轮会话。"""

from dataclasses import dataclass
from uuid import uuid4

from arclet.alconna import AllParam, store_true
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.permission import MESSAGE
from nonebot.typing import T_State
from nonebot_plugin_alconna import (
    Alconna,
    Args,
    CommandMeta,
    Image,
    Match,
    MsgId,
    Option,
    Query,
    UniMessage,
    on_alconna,
)
from nonebot_plugin_alconna.builtins.extensions.reply import ReplyRecordExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession

from src.utils.permission import SuperUserShortcutExtension

from .config import plugin_config
from .content import extract_dialogue_content, extract_follow_up, fetch_message_images
from .image_requirements import HD_SIZE, ImageRequirements
from .image_service import ImageTask, format_image_failure, prepare_image, select_image_task
from .providers import ProviderError
from .reply import send_image_result, send_reaction
from .rules import NON_PRIVATE_RULE
from .schemas import ImageContent, Message


def draw_options() -> tuple[Option, ...]:
    return (
        Option("--image-model", Args["name#生图配置名", str], dest="image_model", help_text="本次使用指定生图模型"),
        Option("--format", Args["type#输出格式", str], help_text="实际输出格式：gif、png、jpeg、webp"),
        Option("--size", Args["size#输出尺寸", str], help_text="实际像素尺寸，如 1024x1024；官方 Images 也支持 auto"),
        Option("--hd", default=False, action=store_true, help_text=f"高清：静态方图 {HD_SIZE}，官方 GIF 自选尺寸"),
        Option("--frames", Args["count#GIF帧数", str], help_text="官方 GIF 帧数（2–16）"),
    )


@dataclass(frozen=True)
class ImageOptions:
    name: str = ""
    output_format: str = ""
    size: str = ""
    hd: bool = False
    frames: str = ""

    def requirements(self) -> ImageRequirements:
        return ImageRequirements.from_options(self.output_format, self.size, hd=self.hd, frames=self.frames)

    def selected_name(self, legacy_name: str) -> str:
        if self.name and legacy_name and self.name != legacy_name:
            raise ProviderError("--image-model 与绘图别名 --model 指定的模型冲突")
        return self.name or legacy_name

    @property
    def supplied(self) -> bool:
        return bool(self.name or self.output_format or self.size or self.hd or self.frames)


draw_command = Alconna(
    "draw",
    Args["content?#描述", AllParam],
    Option("-c|--context", default=False, action=store_true, help_text="使用同一 Responses 生图模型续画"),
    Option("--model", Args["model#生图配置名", str], help_text="旧选项已改义，现为 --image-model 的别名"),
    *draw_options(),
    meta=CommandMeta(
        description="直接使用本群生图模型，识别描述中的格式、尺寸和宽高比",
        example="/draw 画一张 1024 像素见方的动态贴纸",
    ),
)

draw_cmd = on_alconna(
    draw_command,
    use_cmd_start=True,
    block=True,
    rule=NON_PRIVATE_RULE,
    permission=MESSAGE,
    extensions=[ReplyRecordExtension(), TelegramSlashExtension(), SuperUserShortcutExtension()],
)


@dataclass(frozen=True)
class _DrawRound:
    requirements: ImageRequirements
    user_message: Message
    image_record: Message


async def handle_draw(
    matcher: type[Matcher],
    bot: Bot,
    event: Event,
    state: T_State,
    msg_id: MsgId,
    ext: ReplyRecordExtension,
    user: UserSession,
    content: Match[UniMessage],
    *,
    use_context: bool,
    legacy_name: str,
    image_options: ImageOptions,
) -> None:
    try:
        command_requirements = image_options.requirements()
        selected_name = image_options.selected_name(legacy_name)
        text, images = await extract_dialogue_content(content, msg_id, ext, bot, event, state)
    except (ProviderError, ValueError) as error:
        await matcher.finish(str(error), at_sender=True)
    if not text and not images:
        await matcher.finish("请提供绘图描述，输入 /draw -h 查看用法", at_sender=True)
    try:
        # 被引用的内容可以说明画什么，只有本条命令能指定输出规格。
        instruction = content.result.extract_plain_text() if content.available else ""
        requirements = command_requirements.with_prompt(instruction)
        task = await select_image_task(
            user.session_id, requirements, selected_name=selected_name, use_context=use_context, references=bool(images)
        )
    except ProviderError as error:
        await matcher.finish(str(error), at_sender=True)
    session_affinity = uuid4().hex
    rounds: list[_DrawRound] = []

    async def draw_turn(
        prepared: ImageTask,
        current_requirements: ImageRequirements,
        prompt: str,
        references: list[ImageContent] | None,
        message_id: str,
    ) -> None:
        await send_reaction("thinking", message_id=message_id)
        history = [message for turn in rounds for message in (turn.user_message, turn.image_record)]
        try:
            result, image_record = await prepared.run(
                prompt, session_affinity=session_affinity, images=references, history=history
            )
        except (ValueError, ProviderError) as error:
            await send_reaction("fail", message_id=message_id)
            await matcher.finish(format_image_failure(error), at_sender=True)
        await send_reaction("done", message_id=message_id)
        await send_image_result(result)
        if use_context:
            if image_record is None:
                await matcher.finish("生图服务没有返回可续画的图片记录；已停止多轮绘图")
            rounds.append(_DrawRound(current_requirements, Message.user(prompt, references), image_record))

    await draw_turn(task, requirements, text, images, msg_id)
    if not use_context:
        return

    from nonebot_plugin_waiter import prompt

    while True:
        received = await prompt(
            "继续绘图吧（发送「结束」结束绘图，「回滚」撤销上一轮）",
            handler=extract_follow_up,
            timeout=plugin_config.context_timeout,
        )
        if received is None:
            await matcher.finish("等待超时，已结束绘图")
        reply, reply_message_id, reply_event, reply_bot, reply_state = received
        text = reply.extract_plain_text().strip()
        if text in ("结束", "取消"):
            await matcher.finish("已结束绘图")
        if text in ("回滚", "撤销"):
            undo = rounds.pop() if rounds else None
            await UniMessage.text("已回滚上一轮绘图" if undo else "当前没有可回滚的绘图").send()
            continue
        try:
            images = await fetch_message_images(reply.get(Image), reply_event, reply_bot, reply_state)
            if not text and not images:
                continue
            previous = rounds[-1].requirements if rounds else command_requirements
            requirements = previous.follow_up(text)
            prepared = prepare_image(task.model, requirements, use_context=True, references=bool(images))
        except (ProviderError, ValueError) as error:
            # 这一轮参数写错时保留已完成的绘图，用户可以继续修改。
            await UniMessage.text(format_image_failure(error)).send(reply_to=reply_message_id)
            continue
        await draw_turn(prepared, requirements, text, images, reply_message_id)


@draw_cmd.handle()
async def draw_handle(
    bot: Bot,
    event: Event,
    state: T_State,
    msg_id: MsgId,
    ext: ReplyRecordExtension,
    user: UserSession,
    content: Match[UniMessage],
    use_context: Query[bool] = Query("context.value", False),
    model_name: Query[str] = Query("model.model", ""),
    image_name: Query[str] = Query("image_model.name", ""),
    image_format: Query[str] = Query("format.type", ""),
    image_size: Query[str] = Query("size.size", ""),
    image_hd: Query[bool] = Query("hd.value", False),
    image_frames: Query[str] = Query("frames.count", ""),
) -> None:
    await handle_draw(
        draw_cmd,
        bot,
        event,
        state,
        msg_id,
        ext,
        user,
        content,
        use_context=use_context.result,
        legacy_name=model_name.result,
        image_options=ImageOptions(
            image_name.result, image_format.result, image_size.result, image_hd.result, image_frames.result
        ),
    )
