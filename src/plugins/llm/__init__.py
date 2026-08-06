"""大模型对话插件

支持 OpenAI Chat Completions / OpenAI Responses / Anthropic Messages 三种
API 格式，提供多轮对话、推理内容展示、原生 Markdown、Markdown 转图片与 TTS 语音回复。
额度查询按模型选择独立 provider，目前支持 Aperture 与 DeepSeek。
"""

from pathlib import Path

import nonebot
from nonebot import require
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.permission import MESSAGE
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.typing import T_State

require("nonebot_plugin_orm")
require("nonebot_plugin_user")
require("nonebot_plugin_waiter")
require("nonebot_plugin_alconna")
from arclet.alconna import AllParam, store_true
from nonebot_plugin_alconna import (
    Alconna,
    Args,
    CommandMeta,
    Extension,
    Image,
    Match,
    MsgId,
    MultiVar,
    Option,
    Query,
    Subcommand,
    UniMessage,
    get_message_id,
    image_fetch,
    on_alconna,
)
from nonebot_plugin_alconna.builtins.extensions.reply import ReplyRecordExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession

from src.utils.helpers import admin_permission
from src.utils.permission import SUPERUSER

from .config import ModelCapability, plugin_config
from .data_source import (
    clear_available_model_names,
    clear_zssm_model_name,
    clear_zssm_vision_model_name,
    disable_model_names,
    enable_model_names,
    get_available_model_names,
    get_model_name,
    get_model_overview,
    get_tts_model,
    set_model_name,
    set_tts_model,
    set_zssm_model_name,
    set_zssm_vision_model_name,
)
from .handler import LLMHandler, send_reaction
from .providers import ProviderError
from .quota import QuotaError, get_quota, get_quotas
from .rules import MENTION_RULE, NON_PRIVATE_RULE
from .schemas import ImageContent
from .tts import TTSError, get_tts_models

__plugin_meta__ = PluginMetadata(
    name="大模型对话",
    description="接入多种大模型 API，提供智能对话与问答功能",
    usage="使用 /chat 对话（可加 -a 启用工具）、/llm 管理配置，也可在群聊中 @机器人 你好",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)

# Discord 原生斜杠无法完整翻译根参数与选项或嵌套管理树；Discord 继续使用普通消息命令。
llm_cmd = on_alconna(
    Alconna(
        "llm",
        Subcommand(
            "model",
            Subcommand(
                "list",
                Option("-a|--all", default=False, action=store_true, help_text="查看全部模型（仅超级管理员）"),
                Option("-c|--capabilities", default=False, action=store_true, help_text="在模型列表中显示能力"),
                help_text="查看模型列表",
            ),
            Subcommand("set", Args["model#模型名称", str], help_text="设置群组默认模型"),
            Subcommand(
                "enable",
                Args["models?#模型名称", MultiVar(str, flag="+")],
                Option("-a|--all", default=False, action=store_true, help_text="启用本群全部模型"),
                help_text="为本群启用模型（仅超级管理员）",
            ),
            Subcommand(
                "disable",
                Args["models?#模型名称", MultiVar(str, flag="+")],
                Option("-a|--all", default=False, action=store_true, help_text="禁用本群全部模型"),
                help_text="为本群禁用模型（仅超级管理员）",
            ),
            Subcommand("set-zssm", Args["model#模型名称", str], help_text="设置本群解释模型"),
            Subcommand("clear-zssm", help_text="使本群解释模型跟随默认模型"),
            Subcommand("set-zssm-vision", Args["model#模型名称", str], help_text="设置本群解释视觉模型"),
            Subcommand("clear-zssm-vision", help_text="使本群解释视觉模型恢复自动选择"),
            help_text="模型相关设置",
        ),
        Subcommand(
            "tts",
            Subcommand("list", help_text="查看 TTS 模型列表"),
            Subcommand("set", Args["model#模型名称", str], help_text="设置群组默认 TTS 模型"),
            help_text="TTS 模型相关设置",
        ),
        Subcommand(
            "quota",
            Args["model?#模型名称", str],
            Option("-a|--all", default=False, action=store_true, help_text="查询本群全部模型额度"),
            help_text="查询大模型剩余额度",
        ),
        meta=CommandMeta(
            description="管理大模型与 TTS 配置，并查询模型额度",
            example="/llm model list",
        ),
    ),
    use_cmd_start=True,
    block=True,
    rule=NON_PRIVATE_RULE,
    permission=MESSAGE,
    extensions=[
        TelegramSlashExtension(),
    ],
)


chat_command = Alconna(
    "chat",
    Args["content?#内容", AllParam],
    Option("--model", Args["model#模型名称", str], help_text="本次使用指定模型"),
    Option("-c|--context", default=False, action=store_true, help_text="启用多轮对话"),
    Option("-r|--render", default=False, action=store_true, help_text="渲染 Markdown 为图片"),
    Option("-t|--tts", default=False, action=store_true, help_text="使用语音回复"),
    Option("-a|--agent", default=False, action=store_true, help_text="启用工具增强模式"),
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
    ],
)
chat_cmd.shortcut("agent", command="chat -a", prefix=True, fuzzy=True, humanized="agent [选项] <内容>")

llm_cmd.shortcut("quota", command="llm quota", prefix=True, fuzzy=True, humanized="quota [模型名|--all]")
llm_cmd.shortcut("额度", command="llm quota", prefix=True, fuzzy=True, humanized="额度 [模型名|--all]")


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
    ],
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
    enable_tools: bool = False,
) -> LLMHandler:
    """按当前会话设置创建处理器。"""
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

    return LLMHandler(
        name,
        send_markdown=plugin_config.prefer_markdown and not render,
        send_md_pic=render or plugin_config.md_to_pic,
        tts_model=tts_model,
        enable_tools=enable_tools,
    )


@llm_cmd.assign("model.list")
async def llm_model_list_handle(
    bot: Bot,
    event: Event,
    user: UserSession,
    show_all: Query[bool] = Query("model.list.all.value", False),
    show_capabilities: Query[bool] = Query("model.list.capabilities.value", False),
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
        await llm_cmd.finish("本群未启用任何模型，请联系超级管理员配置")

    current = overview.model_name
    zssm_model = overview.zssm_model_name
    vision_model = overview.zssm_vision_model_name
    available = set(available_names)

    def format_model(name: str) -> str:
        labels: list[str] = []
        if show_all.result:
            labels.append("已启用" if name in available else "未启用")
        if name == current:
            labels.append("默认对话")
        if name == zssm_model:
            labels.append("zssm")
        if name == vision_model:
            labels.append("zssm 视觉")
        if show_capabilities.result:
            capabilities = plugin_config.get_model(name).capabilities
            capability_labels = {ModelCapability.TEXT: "文本", ModelCapability.VISION: "视觉"}
            capability_text = "、".join(capability_labels[item] for item in sorted(capabilities))
            labels.append(f"能力：{capability_text or '无'}")
        suffix = f"（{'，'.join(labels)}）" if labels else ""
        return f"- {name}{suffix}"

    names = all_names if show_all.result else available_names
    model_list = "\n".join(format_model(name) for name in names)
    title = "全部模型" if show_all.result else "本群已启用模型"
    access_hint = (
        "\n\n模型管理（超级管理员）："
        "\n- 启用：/llm model enable <模型名...>"
        "\n- 全部启用：/llm model enable --all"
        "\n- 禁用：/llm model disable <模型名...>"
        "\n- 全部禁用：/llm model disable --all"
        if show_all.result
        else ""
    )
    await llm_cmd.finish(
        f"{title}：\n{model_list}\n\n"
        "对话：\n"
        "- 纯对话：/chat --model <模型名> <内容>\n"
        "- 工具增强：/agent --model <模型名> <内容>\n\n"
        "群组设置（管理员）：\n"
        "- 默认对话：/llm model set <模型名>\n"
        "- zssm：/llm model set-zssm <模型名>\n"
        "- zssm 跟随默认：/llm model clear-zssm\n"
        "- zssm 视觉：/llm model set-zssm-vision <模型名>\n"
        f"- zssm 视觉自动选择：/llm model clear-zssm-vision{access_hint}"
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

    try:
        await set_model_name(user.session_id, model.result)
    except ValueError as e:
        await llm_cmd.finish(str(e), at_sender=True)
    await llm_cmd.finish(f"已设置群组默认模型为：{model.result}", at_sender=True)


@llm_cmd.assign("model.enable")
async def llm_model_enable_handle(
    bot: Bot,
    event: Event,
    user: UserSession,
    models: Query[tuple[str, ...]] = Query("model.enable.models", ()),
    enable_all: Query[bool] = Query("model.enable.all.value", False),
):
    if not await SUPERUSER(bot, event):
        await llm_cmd.finish("该指令仅超级管理员可用", at_sender=True)
    if enable_all.result and models.result:
        await llm_cmd.finish("不能同时指定模型和 --all", at_sender=True)
    if enable_all.result:
        all_names = plugin_config.get_model_names()
        if not all_names:
            await llm_cmd.finish("未配置任何模型，请先在 .env 中配置 LLM__MODELS", at_sender=True)
        await enable_model_names(user.session_id, all_names)
        await llm_cmd.finish("已启用本群全部模型", at_sender=True)
    if not models.result:
        await llm_cmd.finish("请指定要启用的模型，或使用 --all 启用全部模型", at_sender=True)
    try:
        await enable_model_names(user.session_id, list(models.result))
    except ValueError as e:
        await llm_cmd.finish(str(e), at_sender=True)
    enabled = "、".join(dict.fromkeys(models.result))
    await llm_cmd.finish(f"已启用本群模型：{enabled}", at_sender=True)


@llm_cmd.assign("model.disable")
async def llm_model_disable_handle(
    bot: Bot,
    event: Event,
    user: UserSession,
    models: Query[tuple[str, ...]] = Query("model.disable.models", ()),
    disable_all: Query[bool] = Query("model.disable.all.value", False),
):
    if not await SUPERUSER(bot, event):
        await llm_cmd.finish("该指令仅超级管理员可用", at_sender=True)
    if disable_all.result and models.result:
        await llm_cmd.finish("不能同时指定模型和 --all", at_sender=True)
    if disable_all.result:
        await clear_available_model_names(user.session_id)
        await llm_cmd.finish("已禁用本群全部模型", at_sender=True)
    if not models.result:
        await llm_cmd.finish("请指定要禁用的模型，或使用 --all 禁用全部模型", at_sender=True)
    try:
        await disable_model_names(user.session_id, list(models.result))
    except ValueError as e:
        await llm_cmd.finish(str(e), at_sender=True)
    disabled = "、".join(dict.fromkeys(models.result))
    await llm_cmd.finish(f"已禁用本群模型：{disabled}", at_sender=True)


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


@llm_cmd.assign("model.set-zssm-vision")
async def llm_model_set_zssm_vision_handle(
    bot: Bot,
    event: Event,
    user: UserSession,
    model: Query[str] = Query("model.set-zssm-vision.model"),
):
    if not await admin_permission()(bot, event):
        await llm_cmd.finish("该指令仅管理员可用", at_sender=True)
    try:
        await set_zssm_vision_model_name(user.session_id, model.result)
    except ValueError as e:
        await llm_cmd.finish(str(e), at_sender=True)
    await llm_cmd.finish(f"已设置本群解释视觉模型为：{model.result}", at_sender=True)


@llm_cmd.assign("model.clear-zssm-vision")
async def llm_model_clear_zssm_vision_handle(bot: Bot, event: Event, user: UserSession):
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
async def llm_quota_handle(
    user: UserSession,
    model: Query[str] = Query("quota.model"),
    query_all: Query[bool] = Query("quota.all.value", False),
):
    if not plugin_config.get_model_names():
        await llm_cmd.finish("未配置任何模型，请先在 .env 中配置 LLM__MODELS")
    names = await get_available_model_names(user.session_id)
    if not names:
        await llm_cmd.finish("本群未启用任何模型，请联系超级管理员配置", at_sender=True)

    if query_all.result and model.available:
        await llm_cmd.finish("不能同时指定模型和 --all", at_sender=True)
    if query_all.result:
        try:
            result = await get_quotas([plugin_config.resolve(name) for name in names])
        except (QuotaError, ValueError) as e:
            await llm_cmd.finish(str(e), at_sender=True)
        await llm_cmd.finish(result, at_sender=True)

    try:
        name = model.result if model.available else await get_model_name(user.session_id)
    except ValueError as e:
        await llm_cmd.finish(str(e), at_sender=True)
    if name not in names:
        await llm_cmd.finish(f"本群未启用的模型：{name}，可用：{'、'.join(names)}", at_sender=True)

    try:
        result = await get_quota(plugin_config.resolve(name))
    except (QuotaError, ValueError) as e:
        await llm_cmd.finish(str(e), at_sender=True)
    await llm_cmd.finish(result, at_sender=True)


async def _extract_dialogue_content(
    content: Match[UniMessage],
    msg_id: MsgId,
    ext: ReplyRecordExtension,
    bot: Bot,
    event: Event,
    state: T_State,
) -> tuple[str, list[ImageContent] | None]:
    """分别提取当前消息与被回复消息，并编码其回复关系。"""
    current_message = content.result if content.available else UniMessage()
    reply_message = UniMessage()
    reply = ext.get_reply(msg_id)
    has_reply = reply is not None
    if reply is not None:
        if not reply.msg:
            raise ValueError("上一条消息内容为空")
        raw_reply_message = reply.msg
        if isinstance(raw_reply_message, str):
            raw_reply_message = event.get_message().__class__(raw_reply_message)
        reply_message = UniMessage.of(raw_reply_message, bot=bot)

    current_text = current_message.extract_plain_text().strip()
    replied_text = reply_message.extract_plain_text().strip()
    current_images = current_message.get(Image)
    replied_images = reply_message.get(Image)
    images = await _fetch_message_images([*current_images, *replied_images], event, bot, state)

    if has_reply and not current_text and not current_images:
        return replied_text, images or None
    if has_reply:
        text = _format_reply_context(
            current_text,
            replied_text,
            current_image_count=len(current_images),
            replied_image_count=len(replied_images),
        )
    else:
        text = current_text
    return text, images or None


def _format_reply_context(
    current_text: str,
    replied_text: str,
    *,
    current_image_count: int,
    replied_image_count: int,
) -> str:
    """明确标记回复目标与当前请求，避免模型把结构本身当成待处理数据。"""
    parts = [
        "【用户正在回复或引用的消息】",
        replied_text or "（无文字）",
        "",
        "【用户本次发送的消息】",
        current_text or "（无文字）",
    ]
    if current_image_count or replied_image_count:
        parts.extend(["", "【图片归属】"])
        if current_image_count and replied_image_count:
            parts.append(
                f"随请求提供的前 {current_image_count} 张图片属于用户本次发送的消息，"
                f"后 {replied_image_count} 张属于用户正在回复或引用的消息。"
            )
        elif current_image_count:
            parts.append(f"随请求提供的 {current_image_count} 张图片均属于用户本次发送的消息。")
        else:
            parts.append(f"随请求提供的 {replied_image_count} 张图片均属于用户正在回复或引用的消息。")
    return "\n".join(parts)


async def _fetch_message_images(
    image_segments: list[Image],
    event: Event,
    bot: Bot,
    state: T_State,
) -> list[ImageContent]:
    """读取一条消息中的全部图片。"""
    images: list[ImageContent] = []
    for image in image_segments:
        data = await image_fetch(event, bot, state, image)
        if not data:
            raise ValueError("图片读取失败")
        images.append(ImageContent.from_bytes(data))
    return images


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
) -> None:
    """执行共享的纯对话或工具增强命令流程。"""
    try:
        text, images = await _extract_dialogue_content(content, msg_id, ext, bot, event, state)
    except ValueError as e:
        await matcher.finish(str(e), at_sender=True)

    if not text and not images:
        command_name = "agent" if enable_tools else "chat"
        await matcher.finish(f"你想问什么呢？输入 /{command_name} -h 查看用法", at_sender=True)

    try:
        handler = await _create_handler(
            user,
            selected_model=model_name.result if model_name.available else "",
            render=render.result,
            use_tts=use_tts.result,
            enable_tools=enable_tools,
        )
    except LLMSetupError as e:
        if e.at_sender:
            await matcher.finish(str(e), at_sender=True)
        await matcher.finish(str(e))

    if use_context.result:
        await _handle_with_context(handler, text, images, finish_matcher=matcher)
        return

    completion = await _ask(handler, text, images, finish_matcher=matcher)
    await handler.send(completion)


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
) -> None:
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
) -> None:
    """把群聊中 @ 机器人的 Alconna 解析结果交给对话流程。"""
    try:
        text, images = await _extract_dialogue_content(content, msg_id, ext, bot, event, state)
    except ValueError as e:
        await UniMessage.text(str(e)).finish(reply_to=msg_id)

    if not text and not images:
        await UniMessage.text("你想问什么呢？").finish(reply_to=msg_id)

    try:
        handler = await _create_handler(
            user,
            selected_model=model_name.result if model_name.available else "",
            render=render.result,
            use_tts=use_tts.result,
            enable_tools=use_agent.result,
        )
    except LLMSetupError as e:
        await UniMessage.text(str(e)).finish(at_sender=e.at_sender, reply_to=msg_id)
    if use_context.result:
        await _handle_with_context(handler, text, images, message_id=msg_id)
        return
    completion = await _ask(handler, text, images, message_id=msg_id)
    await handler.send(completion, reply_to=msg_id)


async def _handle_with_context(
    handler: LLMHandler,
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

    if message_id:
        completion = await _ask(handler, text, images, message_id=message_id, finish_matcher=finish_matcher)
        await handler.send(completion, reply_to=message_id)
    else:
        completion = await _ask(handler, text, images, finish_matcher=finish_matcher)
        await handler.send(completion)

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
            reply_images = await _fetch_message_images(reply.get(Image), reply_event, reply_bot, reply_state)
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
        await handler.send(completion)


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


_sub_plugins = nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
