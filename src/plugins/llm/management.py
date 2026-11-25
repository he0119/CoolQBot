"""/llm 管理与查询命令

模型启用与默认模型设置、TTS 设置，以及额度查询。
"""

from arclet.alconna import store_true
from nonebot.adapters import Bot, Event
from nonebot.permission import MESSAGE
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, MultiVar, Option, Query, Subcommand, on_alconna
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession

from src.utils.helpers import admin_permission
from src.utils.permission import SUPERUSER

from .config import ModelCapability, plugin_config
from .data_source import (
    clear_available_model_names,
    clear_image_model_name,
    clear_zssm_model_name,
    clear_zssm_vision_model_name,
    disable_model_names,
    enable_model_names,
    get_available_model_names,
    get_model_name,
    get_model_overview,
    get_tts_model,
    set_image_model_name,
    set_model_name,
    set_tts_model,
    set_zssm_model_name,
    set_zssm_vision_model_name,
)
from .quota import QuotaError, get_quota, get_quotas
from .rules import NON_PRIVATE_RULE
from .tts import TTSError, get_tts_models

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
            Subcommand("set-image", Args["model#模型名称", str], help_text="设置本群生图模型"),
            Subcommand("clear-image", help_text="使本群生图模型恢复自动选择"),
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

llm_cmd.shortcut("quota", command="llm quota", prefix=True, fuzzy=True, humanized="quota [模型名|--all]")
llm_cmd.shortcut("额度", command="llm quota", prefix=True, fuzzy=True, humanized="额度 [模型名|--all]")


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
    image_model = overview.image_model_name
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
        if name == image_model:
            labels.append("生图")
        if show_capabilities.result:
            capabilities = plugin_config.get_model(name).capabilities
            capability_labels = {
                ModelCapability.TEXT: "文本",
                ModelCapability.VISION: "视觉",
                ModelCapability.IMAGE_GENERATION: "绘图",
            }
            capability_text = "、".join(
                label for capability, label in capability_labels.items() if capability in capabilities
            )
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
        "- zssm 视觉自动选择：/llm model clear-zssm-vision\n"
        "- 生图：/llm model set-image <模型名>\n"
        f"- 生图自动选择：/llm model clear-image{access_hint}"
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


@llm_cmd.assign("model.set-image")
async def llm_model_set_image_handle(
    bot: Bot,
    event: Event,
    user: UserSession,
    model: Query[str] = Query("model.set-image.model"),
):
    if not await admin_permission()(bot, event):
        await llm_cmd.finish("该指令仅管理员可用", at_sender=True)
    try:
        await set_image_model_name(user.session_id, model.result)
    except ValueError as e:
        await llm_cmd.finish(str(e), at_sender=True)
    await llm_cmd.finish(f"已设置本群生图模型为：{model.result}", at_sender=True)


@llm_cmd.assign("model.clear-image")
async def llm_model_clear_image_handle(bot: Bot, event: Event, user: UserSession):
    if not await admin_permission()(bot, event):
        await llm_cmd.finish("该指令仅管理员可用", at_sender=True)
    await clear_image_model_name(user.session_id)
    await llm_cmd.finish("本群生图模型已恢复自动选择", at_sender=True)


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
