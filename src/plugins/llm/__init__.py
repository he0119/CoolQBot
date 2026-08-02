"""大模型对话插件

支持 OpenAI Chat Completions / OpenAI Responses / Anthropic Messages 三种
API 格式，提供多轮对话、推理内容展示、Markdown 转图片与 TTS 语音回复。
"""

from nonebot import require
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

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
    image_fetch,
    on_alconna,
)
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.reply import ReplyMergeExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession

from src.utils.helpers import admin_permission

from .config import plugin_config
from .data_source import get_model_name, get_tts_model, set_model_name, set_tts_model
from .handler import LLMHandler
from .providers import ProviderError
from .schemas import ImageContent
from .tts import TTSError, get_tts_models

__plugin_meta__ = PluginMetadata(
    name="大模型对话",
    description="接入多种大模型 API，提供智能对话与问答功能",
    usage="/llm 你好",
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
            Option("--set", Args["model#模型名称", str], help_text="设置群组默认模型"),
            help_text="模型相关设置",
        ),
        Subcommand(
            "tts",
            Option("-l|--list", help_text="查看 TTS 模型列表"),
            Option("--set", Args["model#模型名称", str], help_text="设置群组默认 TTS 模型"),
            help_text="TTS 模型相关设置",
        ),
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"ai"},
    use_cmd_start=True,
    block=True,
    extensions=[
        ReplyMergeExtension(),
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "ai"}),
    ],
)


@llm_cmd.assign("model.list")
async def llm_model_list_handle(user: UserSession):
    names = plugin_config.get_model_names()
    if not names:
        await llm_cmd.finish("未配置任何模型，请先在 .env 中配置 LLM__MODELS")

    current = await get_model_name(user.session_id)
    model_list = "\n".join(f"- {name}（当前）" if name == current else f"- {name}" for name in names)
    await llm_cmd.finish(
        f"支持的模型列表：\n{model_list}\n"
        "输入 /llm [内容] --model [模型名] 单次指定模型\n"
        "输入 /llm model --set [模型名] 设置群组默认模型"
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

    names = plugin_config.get_model_names()
    if model.result not in names:
        await llm_cmd.finish(f"未启用的模型：{model.result}，可用：{'、'.join(names)}", at_sender=True)

    await set_model_name(user.session_id, model.result)
    await llm_cmd.finish(f"已设置群组默认模型为：{model.result}", at_sender=True)


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

    if not plugin_config.get_model_names():
        await llm_cmd.finish("未配置任何模型，请先在 .env 中配置 LLM__MODELS")

    # 未指定模型时使用群组默认模型
    name = model_name.result if model_name.available else await get_model_name(user.session_id)
    tts_model = await get_tts_model(user.session_id) if use_tts.result else ""
    if use_tts.result and not tts_model:
        await llm_cmd.finish("未设置 TTS 模型，请先使用 /llm tts --set 设置", at_sender=True)

    images = [ImageContent(data=img.result)] if img.available else None
    text = " ".join(content.result) if content.available else ""

    handler = LLMHandler(
        name,
        send_md_pic=render.result or plugin_config.md_to_pic,
        tts_model=tts_model,
    )

    if use_context.result:
        await _handle_with_context(handler, text, images)
        return

    completion = await _ask(handler, text, images)
    await handler.send(completion)


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
        reply = await prompt(
            "继续对话吧（发送「结束」结束对话，「回滚」撤销上一轮）",
            timeout=plugin_config.context_timeout,
        )
        if reply is None:
            await UniMessage.text("等待超时，已结束对话").finish()

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

        completion = await _ask(handler, message, None)
        await handler.send(completion)


async def _ask(handler: LLMHandler, text: str, images: list[ImageContent] | None):
    """请求模型，失败时结束当前会话并提示原因"""
    try:
        return await handler.ask(text, images)
    except ProviderError as e:
        await llm_cmd.finish(f"调用失败：{e}", at_sender=True)
    except ValueError as e:
        await llm_cmd.finish(str(e), at_sender=True)
    except Exception as e:
        logger.opt(exception=e).error("大模型调用出现未预期的错误")
        await llm_cmd.finish("调用失败，请稍后重试", at_sender=True)
