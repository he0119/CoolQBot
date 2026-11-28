"""对话命令

/chat、/agent 与群聊 @ 机器人，以及多轮对话的等待与回滚。
"""

from dataclasses import dataclass
from typing import Never

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
    on_alconna,
)
from nonebot_plugin_alconna.builtins.extensions.reply import ReplyRecordExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession

from src.utils.permission import SuperUserShortcutExtension

from .config import ModelCapability, plugin_config
from .content import extract_dialogue_content, extract_follow_up, fetch_message_images
from .data_source import get_available_model_names, get_model_name, get_tts_model
from .draw import ImageOptions, draw_options, handle_draw
from .draw import draw_cmd as draw_cmd
from .handler import LLMHandler
from .providers import ProviderError
from .reply import ReplySender, send_reaction
from .rules import MENTION_RULE, NON_PRIVATE_RULE
from .schemas import ImageContent
from .tools.image import ImageToolOptions

chat_command = Alconna(
    "chat",
    Args["content?#内容", AllParam],
    Option("--model", Args["model#模型名称", str], help_text="指定聊天模型；-d 时是已改义的 --image-model 别名"),
    *draw_options(),
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

    image_tool = None
    if allow_image:
        try:
            image_tool = ImageToolOptions(image_options.name, image_options.requirements())
        except ProviderError as error:
            raise LLMSetupError(str(error), at_sender=True) from error

    handler = LLMHandler(
        name,
        enable_tools=enable_tools,
        image_tool=image_tool,
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
    allow_image: bool,
    image_options: ImageOptions,
    quote_reply: bool,
) -> None:
    """执行对话，群聊提及使用引用回复。"""

    async def finish(message: str, *, at_sender: bool = False) -> Never:
        if quote_reply:
            await UniMessage.text(message).finish(at_sender=at_sender, reply_to=msg_id)
        if at_sender:
            await matcher.finish(message, at_sender=True)
        await matcher.finish(message)

    if image_options.supplied and not allow_image:
        await finish("图片参数仅可用于 /draw、/chat -d 或 /chat -i", at_sender=not quote_reply)
    try:
        text, images = await extract_dialogue_content(content, msg_id, ext, bot, event, state)
    except ValueError as error:
        await finish(str(error), at_sender=not quote_reply)

    if not text and not images:
        if quote_reply:
            await finish("你想问什么呢？")
        command = "agent" if enable_tools else "chat"
        await finish(f"你想问什么呢？输入 /{command} -h 查看用法", at_sender=True)

    try:
        dialogue = await _create_dialogue(
            user,
            selected_model=model_name.result if model_name.available else "",
            render=render.result,
            use_tts=use_tts.result,
            enable_tools=enable_tools,
            allow_image=allow_image,
            image_options=image_options,
        )
    except LLMSetupError as error:
        await finish(str(error), at_sender=error.at_sender)

    if use_context.result:
        if quote_reply:
            await _handle_with_context(dialogue, text, images, message_id=msg_id)
        else:
            await _handle_with_context(dialogue, text, images, finish_matcher=matcher)
    elif quote_reply:
        completion = await _ask(dialogue.handler, text, images, message_id=msg_id)
        await dialogue.sender.send(completion, reply_to=msg_id)
    else:
        completion = await _ask(dialogue.handler, text, images, finish_matcher=matcher)
        await dialogue.sender.send(completion)


def _register_chat_handler(matcher: type[Matcher], *, quote_reply: bool = False) -> None:
    @matcher.handle()
    async def handle(
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
            await handle_draw(
                matcher,
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
            matcher,
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
            quote_reply=quote_reply,
        )


_register_chat_handler(chat_cmd)
_register_chat_handler(llm_mention, quote_reply=True)


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
            handler=extract_follow_up,
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
