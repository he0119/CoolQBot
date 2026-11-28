"""对话命令

/chat、/agent、/draw 与群聊 @ 机器人，以及多轮对话的等待与回滚。
"""

from dataclasses import dataclass
from uuid import uuid4

from arclet.alconna import AllParam, store_true
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.permission import MESSAGE
from nonebot.typing import T_State
from nonebot_plugin_alconna import (
    Alconna,
    Args,
    CommandMeta,
    Extension,
    Image,
    Match,
    MsgId,
    Option,
    Query,
    UniMessage,
    get_message_id,
    on_alconna,
)
from nonebot_plugin_alconna.builtins.extensions.reply import ReplyRecordExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession

from src.utils.permission import SuperUserShortcutExtension

from .config import ModelCapability, plugin_config
from .content import extract_dialogue_content, fetch_message_images
from .data_source import get_available_model_names, get_model_name, get_tts_model
from .handler import LLMHandler
from .image_service import HD_SIZE, ImageRequirements, ImageTask, select_image_model
from .providers import ProviderError
from .reply import ReplySender, send_image_result, send_reaction
from .rules import MENTION_RULE, NON_PRIVATE_RULE
from .schemas import ImageContent


def _image_options() -> tuple[Option, ...]:
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


chat_command = Alconna(
    "chat",
    Args["content?#内容", AllParam],
    Option("--model", Args["model#模型名称", str], help_text="指定聊天模型；-d 时是已改义的 --image-model 别名"),
    *_image_options(),
    Option("-c|--context", default=False, action=store_true, help_text="启用多轮对话"),
    Option("-r|--render", default=False, action=store_true, help_text="渲染 Markdown 为图片"),
    Option("-t|--tts", default=False, action=store_true, help_text="使用语音回复"),
    Option("-a|--agent", default=False, action=store_true, help_text="启用工具增强模式"),
    Option("-d|--draw", default=False, action=store_true, help_text="直接使用本群生图模型绘图"),
    Option("-i|--image", default=False, action=store_true, help_text="允许模型按需调用本群生图模型"),
    meta=CommandMeta(
        description="与大模型对话，可按次启用工具增强模式",
        example="/chat 你好，或使用 /chat -a 查询成都天气",
    ),
)

chat_cmd = on_alconna(
    chat_command,
    use_cmd_start=True,
    block=True,
    rule=NON_PRIVATE_RULE,
    permission=MESSAGE,
    extensions=[
        ReplyRecordExtension(),
        TelegramSlashExtension(),
        SuperUserShortcutExtension(),
    ],
)
chat_cmd.shortcut("agent", command="chat -a", prefix=True, fuzzy=True, humanized="agent [选项] <内容>")
draw_command = Alconna(
    "draw",
    Args["content?#描述", AllParam],
    Option("-c|--context", default=False, action=store_true, help_text="使用同一 Responses 生图模型续画"),
    Option("--model", Args["model#生图配置名", str], help_text="旧选项已改义，现为 --image-model 的别名"),
    *_image_options(),
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


class MentionChatExtension(Extension):
    """为 @ 对话补上 chat 命令头，让消息交由 Alconna 正常解析。"""

    @property
    def priority(self) -> int:
        return 15

    @property
    def id(self) -> str:
        return "coolqbot.llm:mention_chat"

    async def message_provider(
        self,
        event: Event,
        state: T_State,
        bot: Bot,
        use_origin: bool = False,
    ) -> UniMessage | None:
        """为空的纯回复提供占位消息，使其仍能进入命令包装与回复记录流程。"""
        try:
            if event.get_message():
                return None
        except (NotImplementedError, ValueError):
            return None
        return UniMessage.text(" ")

    async def receive_wrapper(self, bot: Bot, event: Event, command: Alconna, receive: UniMessage) -> UniMessage:
        command_prefix = command.prefixes[0] if command.prefixes else ""
        message = UniMessage.text(f"{command_prefix}{command.command} ")
        message.extend(receive)
        return message


llm_mention = on_alconna(
    chat_command,
    rule=MENTION_RULE,
    permission=MESSAGE,
    priority=15,
    block=True,
    extensions=[
        ReplyRecordExtension(),
        MentionChatExtension(),
        SuperUserShortcutExtension(),
    ],
)


class LLMSetupError(ValueError):
    """模型或输出配置不能用于当前请求。"""

    def __init__(self, message: str, *, at_sender: bool = False) -> None:
        super().__init__(message)
        self.at_sender = at_sender


@dataclass
class Dialogue:
    """一次对话命令用到的请求处理器与回复发送器"""

    handler: LLMHandler
    sender: ReplySender


async def _create_dialogue(
    user: UserSession,
    *,
    selected_model: str = "",
    render: bool = False,
    use_tts: bool = False,
    enable_tools: bool = False,
    allow_image: bool = False,
    image_options: ImageOptions = ImageOptions(),
    has_references: bool = False,
) -> Dialogue:
    """按当前会话设置创建请求处理器与回复发送器。"""
    if not plugin_config.get_model_names():
        raise LLMSetupError("未配置任何模型，请先在 .env 中配置 LLM__MODELS")
    model_names = await get_available_model_names(user.session_id)
    if not model_names:
        raise LLMSetupError("本群未启用任何模型，请联系超级管理员配置", at_sender=True)
    if not any(ModelCapability.TEXT in plugin_config.get_model(name).capabilities for name in model_names):
        raise LLMSetupError("本群未启用支持文本的模型，请联系超级管理员配置", at_sender=True)

    name = selected_model or await get_model_name(user.session_id)
    if name not in model_names:
        raise LLMSetupError(
            f"本群未启用的模型：{name}，可用：{'、'.join(model_names)}",
            at_sender=True,
        )
    if ModelCapability.TEXT not in plugin_config.get_model(name).capabilities:
        raise LLMSetupError(f"模型 {name} 未声明 text 能力，不能用于文本对话", at_sender=True)

    tts_model = await get_tts_model(user.session_id) if use_tts else ""
    if use_tts and not tts_model:
        raise LLMSetupError(
            "未设置 TTS 模型，请先使用 /llm tts set 设置",
            at_sender=True,
        )

    # 聊天中只在 -i/--image 时开放生图，-a 不会自动带上。
    image_model = None
    image_requirements = ImageRequirements()
    if allow_image:
        try:
            image_requirements = image_options.requirements()
            image_model = await select_image_model(
                user.session_id,
                selected_name=image_options.name,
                requirements=image_requirements,
                references=has_references,
            )
        except ProviderError as e:
            raise LLMSetupError(str(e), at_sender=True) from e

    handler = LLMHandler(
        name,
        enable_tools=enable_tools,
        allow_image=allow_image,
        image_model=image_model,
        image_requirements=image_requirements,
        session_id=user.session_id,
    )
    sender = ReplySender(
        send_markdown=plugin_config.prefer_markdown and not render,
        send_md_pic=render or plugin_config.md_to_pic,
        tts_model=tts_model,
        show_thinking=plugin_config.send_thinking,
        log_id=handler.log_id,
    )
    return Dialogue(handler, sender)


async def _handle_dialogue_command(
    matcher: type[Matcher],
    bot: Bot,
    event: Event,
    state: T_State,
    msg_id: MsgId,
    ext: ReplyRecordExtension,
    user: UserSession,
    content: Match[UniMessage],
    model_name: Query[str],
    use_context: Query[bool],
    render: Query[bool],
    use_tts: Query[bool],
    *,
    enable_tools: bool,
    allow_image: bool = False,
    image_options: ImageOptions = ImageOptions(),
) -> None:
    """执行共享的纯对话或工具增强命令流程。"""
    if image_options.supplied and not allow_image:
        await matcher.finish("图片参数仅可用于 /draw、/chat -d 或 /chat -i", at_sender=True)
    try:
        text, images = await extract_dialogue_content(content, msg_id, ext, bot, event, state)
    except ValueError as e:
        await matcher.finish(str(e), at_sender=True)

    if not text and not images:
        command_name = "agent" if enable_tools else "chat"
        await matcher.finish(f"你想问什么呢？输入 /{command_name} -h 查看用法", at_sender=True)

    try:
        dialogue = await _create_dialogue(
            user,
            selected_model=model_name.result if model_name.available else "",
            render=render.result,
            use_tts=use_tts.result,
            enable_tools=enable_tools,
            allow_image=allow_image,
            image_options=image_options,
            has_references=bool(images),
        )
    except LLMSetupError as e:
        if e.at_sender:
            await matcher.finish(str(e), at_sender=True)
        await matcher.finish(str(e))

    if use_context.result:
        await _handle_with_context(dialogue, text, images, finish_matcher=matcher)
        return

    completion = await _ask(dialogue.handler, text, images, finish_matcher=matcher)
    await dialogue.sender.send(completion)


async def _handle_draw(
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
        requirements = image_options.requirements()
        selected_name = image_options.selected_name(legacy_name)
    except ProviderError as e:
        await matcher.finish(str(e), at_sender=True)
    try:
        text, images = await extract_dialogue_content(content, msg_id, ext, bot, event, state)
    except ValueError as e:
        await matcher.finish(str(e), at_sender=True)
    if not text and not images:
        await matcher.finish("请提供绘图描述，输入 /draw -h 查看用法", at_sender=True)
    try:
        # 引用消息保留在模型提示词中，不替本次命令指定输出参数。
        instruction = content.result.extract_plain_text() if content.available else ""
        requirements = requirements.with_prompt(instruction)
        model = await select_image_model(
            user.session_id,
            selected_name=selected_name,
            requirements=requirements,
            use_context=use_context,
            references=bool(images),
        )
    except ProviderError as e:
        await matcher.finish(str(e), at_sender=True)
    task = ImageTask(model, uuid4().hex, use_context=use_context, requirements=requirements)

    async def draw_turn(prompt: str, references: list[ImageContent] | None, message_id: str) -> None:
        await send_reaction("thinking", message_id=message_id)
        try:
            result = await task.run(prompt, references)
        except (ValueError, ProviderError) as e:
            await send_reaction("fail", message_id=message_id)
            await matcher.finish(f"绘图失败：{e}", at_sender=True)
        await send_reaction("done", message_id=message_id)
        await send_image_result(result)

    await draw_turn(text, images, msg_id)
    if not use_context:
        return
    if not task.can_continue:
        await matcher.finish("生图服务没有返回可续画的图片记录；已停止多轮绘图")

    from nonebot_plugin_waiter import prompt

    while True:
        received = await prompt(
            "继续绘图吧（发送「结束」结束绘图，「回滚」撤销上一轮）",
            handler=_extract_reply,
            timeout=plugin_config.context_timeout,
        )
        if received is None:
            await matcher.finish("等待超时，已结束绘图")
        reply, reply_message_id, reply_event, reply_bot, reply_state = received
        text = reply.extract_plain_text().strip()
        if text in ("结束", "取消"):
            await matcher.finish("已结束绘图")
        if text in ("回滚", "撤销"):
            await UniMessage.text("已回滚上一轮绘图" if task.rollback() else "当前没有可回滚的绘图").send()
            continue
        try:
            images = await fetch_message_images(reply.get(Image), reply_event, reply_bot, reply_state)
        except ValueError as e:
            await matcher.finish(str(e), at_sender=True)
        if text or images:
            await draw_turn(text, images, reply_message_id)
            if not task.can_continue:
                await matcher.finish("生图服务没有返回可续画的图片记录；已停止多轮绘图")


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
    await _handle_draw(
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


@chat_cmd.handle()
async def chat_handle(
    bot: Bot,
    event: Event,
    state: T_State,
    msg_id: MsgId,
    ext: ReplyRecordExtension,
    user: UserSession,
    content: Match[UniMessage],
    model_name: Query[str] = Query("model.model"),
    use_context: Query[bool] = Query("context.value", False),
    render: Query[bool] = Query("render.value", False),
    use_tts: Query[bool] = Query("tts.value", False),
    use_agent: Query[bool] = Query("agent.value", False),
    use_draw: Query[bool] = Query("draw.value", False),
    use_image: Query[bool] = Query("image.value", False),
    image_name: Query[str] = Query("image_model.name", ""),
    image_format: Query[str] = Query("format.type", ""),
    image_size: Query[str] = Query("size.size", ""),
    image_hd: Query[bool] = Query("hd.value", False),
    image_frames: Query[str] = Query("frames.count", ""),
) -> None:
    image_options = ImageOptions(
        image_name.result, image_format.result, image_size.result, image_hd.result, image_frames.result
    )
    if use_draw.result:
        await _handle_draw(
            chat_cmd,
            bot,
            event,
            state,
            msg_id,
            ext,
            user,
            content,
            use_context=use_context.result,
            legacy_name=model_name.result if model_name.available else "",
            image_options=image_options,
        )
        return
    await _handle_dialogue_command(
        chat_cmd,
        bot,
        event,
        state,
        msg_id,
        ext,
        user,
        content,
        model_name,
        use_context,
        render,
        use_tts,
        enable_tools=use_agent.result,
        allow_image=use_image.result,
        image_options=image_options,
    )


@llm_mention.handle()
async def llm_mention_handle(
    bot: Bot,
    event: Event,
    state: T_State,
    msg_id: MsgId,
    ext: ReplyRecordExtension,
    user: UserSession,
    content: Match[UniMessage],
    model_name: Query[str] = Query("model.model"),
    use_context: Query[bool] = Query("context.value", False),
    render: Query[bool] = Query("render.value", False),
    use_tts: Query[bool] = Query("tts.value", False),
    use_agent: Query[bool] = Query("agent.value", False),
    use_draw: Query[bool] = Query("draw.value", False),
    use_image: Query[bool] = Query("image.value", False),
    image_name: Query[str] = Query("image_model.name", ""),
    image_format: Query[str] = Query("format.type", ""),
    image_size: Query[str] = Query("size.size", ""),
    image_hd: Query[bool] = Query("hd.value", False),
    image_frames: Query[str] = Query("frames.count", ""),
) -> None:
    """把群聊中 @ 机器人的 Alconna 解析结果交给对话流程。"""
    image_options = ImageOptions(
        image_name.result, image_format.result, image_size.result, image_hd.result, image_frames.result
    )
    if use_draw.result:
        await _handle_draw(
            llm_mention,
            bot,
            event,
            state,
            msg_id,
            ext,
            user,
            content,
            use_context=use_context.result,
            legacy_name=model_name.result if model_name.available else "",
            image_options=image_options,
        )
        return
    if image_options.supplied and not use_image.result:
        await UniMessage.text("图片参数仅可用于 /draw、/chat -d 或 /chat -i").finish(reply_to=msg_id)
    try:
        text, images = await extract_dialogue_content(content, msg_id, ext, bot, event, state)
    except ValueError as e:
        await UniMessage.text(str(e)).finish(reply_to=msg_id)

    if not text and not images:
        await UniMessage.text("你想问什么呢？").finish(reply_to=msg_id)

    try:
        dialogue = await _create_dialogue(
            user,
            selected_model=model_name.result if model_name.available else "",
            render=render.result,
            use_tts=use_tts.result,
            enable_tools=use_agent.result,
            allow_image=use_image.result,
            image_options=image_options,
            has_references=bool(images),
        )
    except LLMSetupError as e:
        await UniMessage.text(str(e)).finish(at_sender=e.at_sender, reply_to=msg_id)
    if use_context.result:
        await _handle_with_context(dialogue, text, images, message_id=msg_id)
        return
    completion = await _ask(dialogue.handler, text, images, message_id=msg_id)
    await dialogue.sender.send(completion, reply_to=msg_id)


async def _handle_with_context(
    dialogue: Dialogue,
    text: str,
    images: list[ImageContent] | None,
    *,
    message_id: str | None = None,
    finish_matcher: type[Matcher] = chat_cmd,
) -> None:
    """多轮对话

    每轮回复后等待下一条消息，支持「结束」与「回滚」指令。
    """
    from nonebot_plugin_waiter import prompt

    handler, sender = dialogue.handler, dialogue.sender
    completion = await _ask(handler, text, images, message_id=message_id, finish_matcher=finish_matcher)
    await sender.send(completion, reply_to=message_id or False)

    while True:
        received = await prompt(
            "继续对话吧（发送「结束」结束对话，「回滚」撤销上一轮）",
            handler=_extract_reply,
            timeout=plugin_config.context_timeout,
        )
        if received is None:
            await UniMessage.text("等待超时，已结束对话").finish()
        reply, reply_message_id, reply_event, reply_bot, reply_state = received

        message = reply.extract_plain_text().strip()
        if message in ("结束", "取消"):
            await UniMessage.text("已结束对话").finish()
        if message in ("回滚", "撤销"):
            if handler.rollback():
                await UniMessage.text("已回滚上一轮对话").send()
            else:
                await UniMessage.text("当前没有可回滚的对话").send()
            continue
        try:
            reply_images = await fetch_message_images(reply.get(Image), reply_event, reply_bot, reply_state)
        except ValueError as e:
            await finish_matcher.finish(str(e), at_sender=True)
        if not message and not reply_images:
            continue

        completion = await _ask(
            handler,
            message,
            reply_images or None,
            message_id=reply_message_id,
            finish_matcher=finish_matcher,
        )
        await sender.send(completion)


def _extract_reply(reply_event: Event, bot: Bot, state: T_State):
    """提取续聊消息及下载其中媒体所需的事件上下文。"""
    message = UniMessage.of(reply_event.get_message(), bot=bot)
    return message, get_message_id(reply_event), reply_event, bot, state


async def _send_request_wait_notice(
    count: int,
    request_count: int,
    tool_call_count: int,
    *,
    message_id: str | None = None,
) -> None:
    """提示用户 Agent 请求仍在进行；首次与后续心跳使用不同文案。"""
    progress = f"模型请求 {request_count}/{plugin_config.max_requests} 次"
    if tool_call_count:
        progress += f"，工具调用 {tool_call_count} 次"
    text = f"⏳ 模型正在处理（{progress}），请稍候……" if count == 1 else f"⏳ 处理仍在进行（{progress}），请再稍候……"
    await UniMessage.text(text).send(reply_to=message_id or True)


async def _ask(
    handler: LLMHandler,
    text: str,
    images: list[ImageContent] | None,
    *,
    message_id: str | None = None,
    finish_matcher: type[Matcher] = chat_cmd,
):
    """请求模型，失败时结束当前会话并提示原因"""
    await send_reaction("thinking", message_id=message_id)

    async def notify_request_wait(count: int, request_count: int, tool_call_count: int) -> None:
        await _send_request_wait_notice(count, request_count, tool_call_count, message_id=message_id)

    try:
        completion = await handler.ask(text, images, on_request_wait=notify_request_wait)
    except ProviderError as e:
        logger.warning("LLM 调用失败（会话={}，错误类型=ProviderError，错误={}）", handler.log_id, e)
        await send_reaction("fail", message_id=message_id)
        await finish_matcher.finish(f"调用失败：{e}", at_sender=True)
    except ValueError as e:
        logger.warning("LLM 调用失败（会话={}，错误类型=ValueError，错误={}）", handler.log_id, e)
        await send_reaction("fail", message_id=message_id)
        await finish_matcher.finish(str(e), at_sender=True)
    except Exception as e:
        logger.opt(exception=e).error(
            "大模型调用出现未预期的错误（会话={}，错误类型={}）",
            handler.log_id,
            type(e).__name__,
        )
        await send_reaction("fail", message_id=message_id)
        await finish_matcher.finish("调用失败，请稍后重试", at_sender=True)

    await send_reaction("done", message_id=message_id)
    return completion
