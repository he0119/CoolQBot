"""大模型对话插件

支持 OpenAI Chat Completions / OpenAI Responses / Anthropic Messages 三种
API 格式，提供多轮对话、推理内容展示、原生 Markdown、Markdown 转图片与 TTS 语音回复。
额度查询按模型选择独立 provider，目前支持 Aperture 与 DeepSeek。
"""

from pathlib import Path

import nonebot
from nonebot import on_message, require
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.rule import Rule, to_me
from nonebot.typing import T_State

require("nonebot_plugin_orm")
require("nonebot_plugin_user")
require("nonebot_plugin_waiter")
require("nonebot_plugin_alconna")
from arclet.alconna import store_true
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaMatch,
    Args,
    CommandMeta,
    Image,
    Match,
    MultiVar,
    Option,
    Query,
    Subcommand,
    UniMessage,
    get_message_id,
    image_fetch,
    on_alconna,
)
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.reply import ReplyMergeExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession

from src.utils.helpers import admin_permission
from src.utils.permission import SUPERUSER

from .config import plugin_config
from .data_source import (
    clear_available_model_names,
    clear_zssm_model_name,
    clear_zssm_vision_model_name,
    get_available_model_names,
    get_model_name,
    get_model_overview,
    get_tts_model,
    set_available_model_names,
    set_model_name,
    set_tts_model,
    set_zssm_model_name,
    set_zssm_vision_model_name,
)
from .handler import LLMHandler, send_reaction
from .providers import ProviderError
from .quota import QuotaError, get_quota
from .rules import is_non_private
from .schemas import ImageContent
from .tts import TTSError, get_tts_models

__plugin_meta__ = PluginMetadata(
    name="大模型对话",
    description="接入多种大模型 API，提供智能对话与问答功能",
    usage="/llm 你好，或在群聊中 @机器人 你好",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)

llm_cmd = on_alconna(
    Alconna(
        "llm",
        Args["content?#内容", MultiVar(str, flag="+")]["img?#图片", Image],
        Option("--model", Args["model#模型名称", str], help_text="本次使用指定模型"),
        Option("-c|--context", default=False, action=store_true, help_text="启用多轮对话"),
        Option("-r|--render", default=False, action=store_true, help_text="渲染 Markdown 为图片"),
        Option("-t|--tts", default=False, action=store_true, help_text="使用语音回复"),
        Subcommand(
            "model",
            Option("-l|--list", help_text="查看模型列表"),
            Option("-a|--all", default=False, action=store_true, help_text="查看全部模型（仅超级管理员）"),
            Option("-c|--capabilities", default=False, action=store_true, help_text="在模型列表中显示能力"),
            Option("--set", Args["model#模型名称", str], help_text="设置群组默认模型"),
            Option(
                "--set-available",
                Args["models#模型名称", MultiVar(str, flag="+")],
                help_text="设置本群可用模型（仅超级管理员）",
            ),
            Option("--clear-available", action=store_true, help_text="清空本群可用模型（仅超级管理员）"),
            Option("--set-zssm", Args["model#模型名称", str], help_text="设置本群解释模型"),
            Option("--clear-zssm", action=store_true, help_text="使本群解释模型跟随默认模型"),
            Option("--set-vision", Args["model#模型名称", str], help_text="设置本群解释视觉模型"),
            Option("--clear-vision", action=store_true, help_text="使本群解释视觉模型恢复自动选择"),
            help_text="模型相关设置",
        ),
        Subcommand(
            "tts",
            Option("-l|--list", help_text="查看 TTS 模型列表"),
            Option("--set", Args["model#模型名称", str], help_text="设置群组默认 TTS 模型"),
            help_text="TTS 模型相关设置",
        ),
        Subcommand(
            "quota",
            Args["model?#模型名称", str],
            help_text="查询大模型剩余额度",
        ),
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    use_cmd_start=True,
    block=True,
    rule=Rule(is_non_private),
    extensions=[
        ReplyMergeExtension(),
        TelegramSlashExtension(),
        DiscordSlashExtension(),
    ],
)

llm_cmd.shortcut("quota", command="llm quota", prefix=True, fuzzy=True, humanized="quota [模型名]")
llm_cmd.shortcut("额度", command="llm quota", prefix=True, fuzzy=True, humanized="额度 [模型名]")


async def _should_handle_mention(event: Event) -> bool:
    """按配置启用快捷对话，并避免带非空前缀的命令被重复处理。"""
    if not plugin_config.respond_to_mention:
        return False
    text = event.get_plaintext().lstrip()
    return not any(prefix and text.startswith(prefix) for prefix in nonebot.get_driver().config.command_start)


llm_mention = on_message(
    rule=Rule(is_non_private) & to_me() & Rule(_should_handle_mention),
    priority=15,
    block=True,
)


class LLMSetupError(ValueError):
    """模型或输出配置不能用于当前请求。"""

    def __init__(self, message: str, *, at_sender: bool = False) -> None:
        super().__init__(message)
        self.at_sender = at_sender


async def _create_handler(
    user: UserSession,
    *,
    selected_model: str = "",
    render: bool = False,
    use_tts: bool = False,
) -> LLMHandler:
    """按当前会话设置创建处理器。"""
    if not plugin_config.get_model_names():
        raise LLMSetupError("未配置任何模型，请先在 .env 中配置 LLM__MODELS")
    model_names = await get_available_model_names(user.session_id)
    if not model_names:
        raise LLMSetupError("本群未开放任何模型，请联系超级管理员配置", at_sender=True)

    name = selected_model or await get_model_name(user.session_id)
    if name not in model_names:
        raise LLMSetupError(
            f"本群未启用的模型：{name}，可用：{'、'.join(model_names)}",
            at_sender=True,
        )

    tts_model = await get_tts_model(user.session_id) if use_tts else ""
    if use_tts and not tts_model:
        raise LLMSetupError(
            "未设置 TTS 模型，请先使用 /llm tts --set 设置",
            at_sender=True,
        )

    return LLMHandler(
        name,
        send_markdown=plugin_config.prefer_markdown and not render,
        send_md_pic=render or plugin_config.md_to_pic,
        tts_model=tts_model,
    )


@llm_cmd.assign("model.list")
async def llm_model_list_handle(
    bot: Bot,
    event: Event,
    user: UserSession,
    show_all: Query[bool] = Query("model.all.value", False),
    show_capabilities: Query[bool] = Query("model.capabilities.value", False),
):
    all_names = plugin_config.get_model_names()
    if not all_names:
        await llm_cmd.finish("未配置任何模型，请先在 .env 中配置 LLM__MODELS")
    overview = await get_model_overview(user.session_id)
    available_names = overview.available_model_names
    is_superuser = await SUPERUSER(bot, event)
    if show_all.result and not is_superuser:
        await llm_cmd.finish("该参数仅超级管理员可用", at_sender=True)
    if not available_names and not show_all.result:
        await llm_cmd.finish("本群未开放任何模型，请联系超级管理员配置")

    current = overview.model_name
    zssm_model = overview.zssm_model_name
    vision_model = overview.zssm_vision_model_name
    available = set(available_names)

    def format_model(name: str) -> str:
        labels: list[str] = []
        if show_all.result:
            labels.append("已开放" if name in available else "未开放")
        if name == current:
            labels.append("当前")
        if name == zssm_model:
            labels.append("zssm")
        if name == vision_model:
            labels.append("zssm 视觉")
        if show_capabilities.result:
            capabilities = plugin_config.get_model(name).capabilities
            capability_text = "、".join("视觉" if item == "vision" else item for item in sorted(capabilities))
            labels.append(f"能力：{capability_text or '无'}")
        suffix = f"（{'，'.join(labels)}）" if labels else ""
        return f"- {name}{suffix}"

    names = all_names if show_all.result else available_names
    model_list = "\n".join(format_model(name) for name in names)
    title = "全部模型列表" if show_all.result else "支持的模型列表"
    access_hint = "\n输入 /llm model --set-available [模型名...] 设置本群开放模型" if show_all.result else ""
    await llm_cmd.finish(
        f"{title}：\n{model_list}\n"
        "输入 /llm --model [模型名] [内容] 单次指定模型\n"
        f"输入 /llm model --set [模型名] 设置群组默认模型{access_hint}"
    )


@llm_cmd.assign("model.set")
async def llm_model_set_handle(
    bot: Bot,
    event: Event,
    user: UserSession,
    model: Query[str] = Query("model.set.model"),
):
    # 影响整个群组的设置仅管理员可用
    if not await admin_permission()(bot, event):
        await llm_cmd.finish("该指令仅管理员可用", at_sender=True)

    names = await get_available_model_names(user.session_id)
    if model.result not in names:
        await llm_cmd.finish(f"本群未启用的模型：{model.result}，可用：{'、'.join(names)}", at_sender=True)

    await set_model_name(user.session_id, model.result)
    await llm_cmd.finish(f"已设置群组默认模型为：{model.result}", at_sender=True)


@llm_cmd.assign("model.set-available")
async def llm_model_set_available_handle(
    bot: Bot,
    event: Event,
    user: UserSession,
    models: Query[tuple[str, ...]] = Query("model.set-available.models"),
):
    if not await SUPERUSER(bot, event):
        await llm_cmd.finish("该指令仅超级管理员可用", at_sender=True)
    try:
        available = await set_available_model_names(user.session_id, list(models.result))
    except ValueError as e:
        await llm_cmd.finish(str(e), at_sender=True)
    await llm_cmd.finish(f"已设置本群可用模型：{'、'.join(available)}", at_sender=True)


@llm_cmd.assign("model.clear-available")
async def llm_model_clear_available_handle(bot: Bot, event: Event, user: UserSession):
    if not await SUPERUSER(bot, event):
        await llm_cmd.finish("该指令仅超级管理员可用", at_sender=True)
    await clear_available_model_names(user.session_id)
    await llm_cmd.finish("已清空本群可用模型", at_sender=True)


@llm_cmd.assign("model.set-zssm")
async def llm_model_set_zssm_handle(
    bot: Bot,
    event: Event,
    user: UserSession,
    model: Query[str] = Query("model.set-zssm.model"),
):
    if not await admin_permission()(bot, event):
        await llm_cmd.finish("该指令仅管理员可用", at_sender=True)
    try:
        await set_zssm_model_name(user.session_id, model.result)
    except ValueError as e:
        await llm_cmd.finish(str(e), at_sender=True)
    await llm_cmd.finish(f"已设置本群解释模型为：{model.result}", at_sender=True)


@llm_cmd.assign("model.clear-zssm")
async def llm_model_clear_zssm_handle(bot: Bot, event: Event, user: UserSession):
    if not await admin_permission()(bot, event):
        await llm_cmd.finish("该指令仅管理员可用", at_sender=True)
    await clear_zssm_model_name(user.session_id)
    await llm_cmd.finish("本群解释模型已改为跟随默认模型", at_sender=True)


@llm_cmd.assign("model.set-vision")
async def llm_model_set_vision_handle(
    bot: Bot,
    event: Event,
    user: UserSession,
    model: Query[str] = Query("model.set-vision.model"),
):
    if not await admin_permission()(bot, event):
        await llm_cmd.finish("该指令仅管理员可用", at_sender=True)
    try:
        await set_zssm_vision_model_name(user.session_id, model.result)
    except ValueError as e:
        await llm_cmd.finish(str(e), at_sender=True)
    await llm_cmd.finish(f"已设置本群解释视觉模型为：{model.result}", at_sender=True)


@llm_cmd.assign("model.clear-vision")
async def llm_model_clear_vision_handle(bot: Bot, event: Event, user: UserSession):
    if not await admin_permission()(bot, event):
        await llm_cmd.finish("该指令仅管理员可用", at_sender=True)
    await clear_zssm_vision_model_name(user.session_id)
    await llm_cmd.finish("本群解释视觉模型已恢复自动选择", at_sender=True)


@llm_cmd.assign("tts.list")
async def llm_tts_list_handle(user: UserSession):
    try:
        models = await get_tts_models()
    except TTSError as e:
        await llm_cmd.finish(str(e))

    if not models:
        await llm_cmd.finish("未找到可用的 TTS 模型")

    current = await get_tts_model(user.session_id)
    model_list = "\n".join(f"- {name}（当前）" if name == current else f"- {name}" for name in models)
    await llm_cmd.finish(f"支持的 TTS 模型列表：\n{model_list}")


@llm_cmd.assign("tts.set")
async def llm_tts_set_handle(
    bot: Bot,
    event: Event,
    user: UserSession,
    model: Query[str] = Query("tts.set.model"),
):
    # 影响整个群组的设置仅管理员可用
    if not await admin_permission()(bot, event):
        await llm_cmd.finish("该指令仅管理员可用", at_sender=True)

    try:
        models = await get_tts_models()
    except TTSError as e:
        await llm_cmd.finish(str(e))

    if model.result not in models:
        await llm_cmd.finish(f"未找到 TTS 模型：{model.result}，可用：{'、'.join(models)}", at_sender=True)

    await set_tts_model(user.session_id, model.result)
    await llm_cmd.finish(f"已设置群组默认 TTS 模型为：{model.result}", at_sender=True)


@llm_cmd.assign("quota")
async def llm_quota_handle(user: UserSession, model: Query[str] = Query("quota.model")):
    if not plugin_config.get_model_names():
        await llm_cmd.finish("未配置任何模型，请先在 .env 中配置 LLM__MODELS")
    names = await get_available_model_names(user.session_id)
    if not names:
        await llm_cmd.finish("本群未开放任何模型，请联系超级管理员配置", at_sender=True)

    name = model.result if model.available else await get_model_name(user.session_id)
    if name not in names:
        await llm_cmd.finish(f"本群未启用的模型：{name}，可用：{'、'.join(names)}", at_sender=True)

    try:
        result = await get_quota(plugin_config.resolve(name))
    except QuotaError as e:
        await llm_cmd.finish(str(e), at_sender=True)
    await llm_cmd.finish(result, at_sender=True)


@llm_cmd.handle()
async def llm_handle(
    user: UserSession,
    content: Match[tuple[str, ...]],
    img: Match[bytes] = AlconnaMatch("img", image_fetch),
    model_name: Query[str] = Query("model.model"),
    use_context: Query[bool] = Query("context.value", False),
    render: Query[bool] = Query("render.value", False),
    use_tts: Query[bool] = Query("tts.value", False),
):
    if not content.available and not img.available:
        await llm_cmd.finish("你想问什么呢？输入 /llm -h 查看用法", at_sender=True)

    images: list[ImageContent] | None = None
    if img.available:
        try:
            images = [ImageContent.from_bytes(img.result)]
        except ValueError as e:
            await llm_cmd.finish(str(e), at_sender=True)
    text = " ".join(content.result) if content.available else ""

    try:
        handler = await _create_handler(
            user,
            selected_model=model_name.result if model_name.available else "",
            render=render.result,
            use_tts=use_tts.result,
        )
    except LLMSetupError as e:
        if e.at_sender:
            await llm_cmd.finish(str(e), at_sender=True)
        await llm_cmd.finish(str(e))

    if use_context.result:
        await _handle_with_context(handler, text, images)
        return

    completion = await _ask(handler, text, images)
    await handler.send(completion)


@llm_mention.handle()
async def llm_mention_handle(
    bot: Bot,
    event: Event,
    state: T_State,
    user: UserSession,
) -> None:
    """把群聊中 @ 机器人的内容直接交给默认模型。"""
    message_id = get_message_id(event)
    message = UniMessage.of(event.get_message(), bot=bot)
    text = message.extract_plain_text().strip()
    images: list[ImageContent] = []
    try:
        for image in message.get(Image):
            data = await image_fetch(event, bot, state, image)
            if not data:
                raise ValueError("图片读取失败")
            images.append(ImageContent.from_bytes(data))
    except ValueError as e:
        await UniMessage.text(str(e)).finish(reply_to=message_id)

    if not text and not images:
        await UniMessage.text("你想问什么呢？").finish(reply_to=message_id)

    try:
        handler = await _create_handler(user)
    except LLMSetupError as e:
        await UniMessage.text(str(e)).finish(at_sender=e.at_sender, reply_to=message_id)
    completion = await _ask(handler, text, images or None, message_id=message_id)
    await handler.send(completion, reply_to=message_id)


async def _handle_with_context(
    handler: LLMHandler,
    text: str,
    images: list[ImageContent] | None,
) -> None:
    """多轮对话

    每轮回复后等待下一条消息，支持「结束」与「回滚」指令。
    """
    from nonebot_plugin_waiter import prompt

    completion = await _ask(handler, text, images)
    await handler.send(completion)

    while True:
        received = await prompt(
            "继续对话吧（发送「结束」结束对话，「回滚」撤销上一轮）",
            handler=_extract_reply,
            timeout=plugin_config.context_timeout,
        )
        if received is None:
            await UniMessage.text("等待超时，已结束对话").finish()
        reply, reply_message_id = received

        message = reply.extract_plain_text().strip()
        if message in ("结束", "取消"):
            await UniMessage.text("已结束对话").finish()
        if message in ("回滚", "撤销"):
            if handler.rollback():
                await UniMessage.text("已回滚上一轮对话").send()
            else:
                await UniMessage.text("当前没有可回滚的对话").send()
            continue
        if not message:
            continue

        completion = await _ask(handler, message, None, message_id=reply_message_id)
        await handler.send(completion)


def _extract_reply(reply_event: Event):
    """提取续聊消息，并在 waiter 事件上下文中保存其消息 ID"""
    return reply_event.get_message(), get_message_id(reply_event)


async def _send_tool_wait_notice(
    count: int,
    request_count: int,
    tool_call_count: int,
    *,
    message_id: str | None = None,
) -> None:
    """提示用户工具调用仍在进行；首次与后续心跳使用不同文案。"""
    progress = f"模型请求 {request_count} 次，工具调用 {tool_call_count} 个"
    text = f"🔍 正在查询资料（{progress}），请稍候……" if count == 1 else f"⏳ 查询仍在进行（{progress}），请再稍候……"
    await UniMessage.text(text).send(reply_to=message_id or True)


async def _ask(
    handler: LLMHandler,
    text: str,
    images: list[ImageContent] | None,
    *,
    message_id: str | None = None,
):
    """请求模型，失败时结束当前会话并提示原因"""
    await send_reaction("thinking", message_id=message_id)

    async def notify_tool_wait(count: int, request_count: int, tool_call_count: int) -> None:
        await _send_tool_wait_notice(count, request_count, tool_call_count, message_id=message_id)

    try:
        completion = await handler.ask(text, images, on_tool_wait=notify_tool_wait)
    except ProviderError as e:
        logger.warning("LLM 调用失败（会话={}，错误类型=ProviderError）", handler.log_id)
        await send_reaction("fail", message_id=message_id)
        await llm_cmd.finish(f"调用失败：{e}", at_sender=True)
    except ValueError as e:
        logger.warning("LLM 调用失败（会话={}，错误类型=ValueError）", handler.log_id)
        await send_reaction("fail", message_id=message_id)
        await llm_cmd.finish(str(e), at_sender=True)
    except Exception as e:
        logger.opt(exception=e).error("大模型调用出现未预期的错误")
        await send_reaction("fail", message_id=message_id)
        await llm_cmd.finish("调用失败，请稍后重试", at_sender=True)

    await send_reaction("done", message_id=message_id)
    return completion


_sub_plugins = nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
