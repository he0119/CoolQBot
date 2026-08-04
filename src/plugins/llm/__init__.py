"""大模型对话插件

支持 OpenAI Chat Completions / OpenAI Responses / Anthropic Messages 三种
API 格式，提供多轮对话、推理内容展示、原生 Markdown、Markdown 转图片与 TTS 语音回复。
额度查询按模型选择独立 provider，目前支持 Aperture 与 DeepSeek。
"""

from dataclasses import dataclass
from pathlib import Path

import nonebot
from nonebot import on_message, require
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.matcher import Matcher
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
from nonebot_plugin_alconna.builtins.extensions.reply import ReplyMergeExtension
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
from .quota import QuotaError, get_quota
from .rules import is_non_private
from .schemas import ImageContent
from .tts import TTSError, get_tts_models

__plugin_meta__ = PluginMetadata(
    name="大模型对话",
    description="接入多种大模型 API，提供智能对话与问答功能",
    usage="使用 /chat 纯对话、/agent 工具问答、/llm 管理配置，也可在群聊中 @机器人 你好",
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
            help_text="查询大模型剩余额度",
        ),
        meta=CommandMeta(
            description="管理大模型与 TTS 配置，并查询模型额度",
            example="/llm model list",
        ),
    ),
    use_cmd_start=True,
    block=True,
    rule=Rule(is_non_private),
    extensions=[
        TelegramSlashExtension(),
    ],
)


def _build_dialogue_command(name: str, *, description: str, example: str) -> Alconna:
    """构造共享参数的纯对话或工具增强命令。"""
    options = [
        Option("--model", Args["model#模型名称", str], help_text="本次使用指定模型"),
        Option("-c|--context", default=False, action=store_true, help_text="启用多轮对话"),
        Option("-r|--render", default=False, action=store_true, help_text="渲染 Markdown 为图片"),
        Option("-t|--tts", default=False, action=store_true, help_text="使用语音回复"),
    ]
    return Alconna(
        name,
        Args["content?#内容", MultiVar(str, flag="+")]["img?#图片", Image],
        *options,
        meta=CommandMeta(description=description, example=example),
    )


chat_command = _build_dialogue_command(
    "chat",
    description="不使用工具，直接与大模型对话",
    example="/chat 你好，或在群聊中 @机器人 你好",
)

chat_cmd = on_alconna(
    chat_command,
    use_cmd_start=True,
    block=True,
    rule=Rule(is_non_private),
    extensions=[
        ReplyMergeExtension(),
        TelegramSlashExtension(),
    ],
)

agent_command = _build_dialogue_command(
    "agent",
    description="允许模型调用包括网页搜索在内的工具完成查询与问答",
    example="/agent 查询成都天气",
)

agent_cmd = on_alconna(
    agent_command,
    use_cmd_start=True,
    block=True,
    rule=Rule(is_non_private),
    extensions=[
        ReplyMergeExtension(),
        TelegramSlashExtension(),
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


@dataclass(frozen=True)
class ChatRequest:
    """统一后的对话文本与选项。"""

    text: str
    model_name: str
    use_context: bool
    render: bool
    use_tts: bool


def _parse_chat_text(text: str) -> ChatRequest:
    """使用 `/chat` 的 Alconna 定义解析 @ 对话参数。"""
    result = chat_command.parse(f"/chat {text}".rstrip())
    if not result.matched:
        raise LLMSetupError("对话参数有误，请输入 /chat -h 查看用法", at_sender=True)
    content: tuple[str, ...] = result.query("content", ())
    if content and content[0] in {"-s", "--search"}:
        raise LLMSetupError("纯对话不支持网页搜索，请使用 /agent", at_sender=True)
    return ChatRequest(
        text=" ".join(content),
        model_name=result.query("model.model", ""),
        use_context=result.query("context.value", False),
        render=result.query("render.value", False),
        use_tts=result.query("tts.value", False),
    )


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
        enable_web_search=enable_tools,
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
async def llm_quota_handle(user: UserSession, model: Query[str] = Query("quota.model")):
    if not plugin_config.get_model_names():
        await llm_cmd.finish("未配置任何模型，请先在 .env 中配置 LLM__MODELS")
    names = await get_available_model_names(user.session_id)
    if not names:
        await llm_cmd.finish("本群未启用任何模型，请联系超级管理员配置", at_sender=True)

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


async def _handle_dialogue_command(
    matcher: type[Matcher],
    user: UserSession,
    content: Match[tuple[str, ...]],
    img: Match[bytes],
    model_name: Query[str],
    use_context: Query[bool],
    render: Query[bool],
    use_tts: Query[bool],
    *,
    enable_tools: bool,
) -> None:
    """执行共享的纯对话或工具增强命令流程。"""
    if not content.available and not img.available:
        command_name = "agent" if enable_tools else "chat"
        await matcher.finish(f"你想问什么呢？输入 /{command_name} -h 查看用法", at_sender=True)
    if not enable_tools and content.available and content.result[0] in {"-s", "--search"}:
        await matcher.finish("纯对话不支持网页搜索，请使用 /agent", at_sender=True)

    images: list[ImageContent] | None = None
    if img.available:
        try:
            images = [ImageContent.from_bytes(img.result)]
        except ValueError as e:
            await matcher.finish(str(e), at_sender=True)
    text = " ".join(content.result) if content.available else ""

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
    user: UserSession,
    content: Match[tuple[str, ...]],
    img: Match[bytes] = AlconnaMatch("img", image_fetch),
    model_name: Query[str] = Query("model.model"),
    use_context: Query[bool] = Query("context.value", False),
    render: Query[bool] = Query("render.value", False),
    use_tts: Query[bool] = Query("tts.value", False),
) -> None:
    await _handle_dialogue_command(
        chat_cmd,
        user,
        content,
        img,
        model_name,
        use_context,
        render,
        use_tts,
        enable_tools=False,
    )


@agent_cmd.handle()
async def agent_handle(
    user: UserSession,
    content: Match[tuple[str, ...]],
    img: Match[bytes] = AlconnaMatch("img", image_fetch),
    model_name: Query[str] = Query("model.model"),
    use_context: Query[bool] = Query("context.value", False),
    render: Query[bool] = Query("render.value", False),
    use_tts: Query[bool] = Query("tts.value", False),
) -> None:
    await _handle_dialogue_command(
        agent_cmd,
        user,
        content,
        img,
        model_name,
        use_context,
        render,
        use_tts,
        enable_tools=True,
    )


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

    try:
        request = _parse_chat_text(text)
    except LLMSetupError as e:
        await UniMessage.text(str(e)).finish(at_sender=e.at_sender, reply_to=message_id)

    if not request.text and not images:
        await UniMessage.text("你想问什么呢？").finish(reply_to=message_id)

    try:
        handler = await _create_handler(
            user,
            selected_model=request.model_name,
            render=request.render,
            use_tts=request.use_tts,
            enable_tools=False,
        )
    except LLMSetupError as e:
        await UniMessage.text(str(e)).finish(at_sender=e.at_sender, reply_to=message_id)
    if request.use_context:
        await _handle_with_context(handler, request.text, images or None, message_id=message_id)
        return
    completion = await _ask(handler, request.text, images or None, message_id=message_id)
    await handler.send(completion, reply_to=message_id)


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

        completion = await _ask(
            handler,
            message,
            None,
            message_id=reply_message_id,
            finish_matcher=finish_matcher,
        )
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
    finish_matcher: type[Matcher] = chat_cmd,
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
        await finish_matcher.finish(f"调用失败：{e}", at_sender=True)
    except ValueError as e:
        logger.warning("LLM 调用失败（会话={}，错误类型=ValueError）", handler.log_id)
        await send_reaction("fail", message_id=message_id)
        await finish_matcher.finish(str(e), at_sender=True)
    except Exception as e:
        logger.opt(exception=e).error("大模型调用出现未预期的错误")
        await send_reaction("fail", message_id=message_id)
        await finish_matcher.finish("调用失败，请稍后重试", at_sender=True)

    await send_reaction("done", message_id=message_id)
    return completion


_sub_plugins = nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
