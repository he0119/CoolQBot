"""回复消息并发送 zssm，让现有 LLM 解释其中内容。"""

from pathlib import Path

from arclet.alconna import AllParam, store_true
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.permission import MESSAGE
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.typing import T_State
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, MsgId, Option, Query, UniMessage, on_alconna
from nonebot_plugin_alconna.builtins.extensions.reply import ReplyRecordExtension
from nonebot_plugin_alconna.uniseg import Image
from nonebot_plugin_user import UserSession

from ...config import ModelCapability, plugin_config
from ...data_source import (
    get_available_model_names,
    get_zssm_model_name,
    get_zssm_vision_model_name,
)
from ...handler import LLMHandler, send_reaction, split_content
from ...providers import ProviderError
from ...rules import NON_PRIVATE_RULE
from .data_source import (
    build_user_prompt,
    describe_images,
    fetch_images,
    format_explain_response,
    load_resources,
    resolve_vision_fallback,
)

__plugin_meta__ = PluginMetadata(
    name="这是什么",
    description="使用大模型解释回复或输入的文字、图片、网页与 PDF",
    usage="回复一条消息并发送 zssm，可用 --model 临时指定模型、-a 启用联网工具，并在后面补充关注点",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)

SYSTEM_PROMPT = Path(__file__).with_name("prompt.txt").read_text(encoding="utf-8")

zssm_cmd = on_alconna(
    Alconna(
        "zssm",
        Args["content?", AllParam],
        Option("--model", Args["model#模型名称", str], help_text="本次使用指定模型"),
        Option("-a|--agent", default=False, action=store_true, help_text="启用联网搜索等工具"),
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    block=True,
    rule=NON_PRIVATE_RULE,
    permission=MESSAGE,
    extensions=[ReplyRecordExtension()],
)


@zssm_cmd.handle()
async def zssm_handle(
    msg_id: MsgId,
    ext: ReplyRecordExtension,
    event: Event,
    bot: Bot,
    state: T_State,
    user: UserSession,
    content: Match[UniMessage],
    selected_model: Query[str] = Query("model.model"),
    use_agent: Query[bool] = Query("agent.value", False),
) -> None:
    """收集被回复消息与关注点，并交给解释模式处理。"""
    current_message = content.result if content.available else UniMessage()
    reply = ext.get_reply(msg_id)

    if reply:
        if not reply.msg:
            await UniMessage.text("上一条消息内容为空").finish(reply_to=msg_id)
        reply_message = reply.msg
        if isinstance(reply_message, str):
            reply_message = event.get_message().__class__(reply_message)
        target_message = UniMessage.of(reply_message, bot=bot)
        focus_message = current_message
    else:
        target_message = current_message
        focus_message = UniMessage()

    target = target_message.extract_plain_text().strip()
    focus = focus_message.extract_plain_text().strip()
    images = [*target_message.get(Image), *focus_message.get(Image)]
    if not target and not focus and not images:
        await UniMessage.text("请回复或输入需要解释的内容").finish(reply_to=msg_id)

    if not plugin_config.get_model_names():
        await UniMessage.text("未配置任何模型，请先在 .env 中配置 LLM__MODELS").finish(reply_to=msg_id)
    names = await get_available_model_names(user.session_id)
    if not names:
        await UniMessage.text("本群未启用任何模型，请联系超级管理员配置").finish(reply_to=msg_id)
    text_names = [name for name in names if ModelCapability.TEXT in plugin_config.get_model(name).capabilities]
    if not text_names:
        await UniMessage.text("本群未启用支持文本的模型，请联系超级管理员配置").finish(reply_to=msg_id)
    model_name = selected_model.result if selected_model.available else await get_zssm_model_name(user.session_id)
    if model_name not in names:
        await UniMessage.text(f"本群未启用解释模型：{model_name}，可用：{'、'.join(names)}").finish(reply_to=msg_id)
    if model_name not in text_names:
        await UniMessage.text(f"解释模型 {model_name} 未声明 text 能力，不能用于文本解释").finish(reply_to=msg_id)
    vision_model = ""
    try:
        vision_model = resolve_vision_fallback(
            model_name,
            await get_zssm_vision_model_name(user.session_id),
            has_images=bool(images),
        )
    except ValueError as e:
        await UniMessage.text(str(e)).finish(reply_to=msg_id)

    logger.info(
        "解释模式开始（模型={}，视觉模型={}，目标字符={}，关注字符={}，图片={}）",
        model_name,
        vision_model or "无需",
        len(target),
        len(focus),
        len(images),
    )
    await send_reaction("thinking", message_id=msg_id)
    stage = "输入准备"
    handler: LLMHandler | None = None
    try:
        image_contents = await fetch_images(images, event, bot, state)
        resources = await load_resources(target, focus)
        image_descriptions = ""
        vision_completion = None
        final_images = image_contents or None
        if image_contents and vision_model:
            stage = "视觉模型请求"
            image_descriptions, vision_completion = await describe_images(vision_model, image_contents)
            final_images = None

        user_prompt = build_user_prompt(
            target,
            focus,
            len(image_contents),
            resources,
            image_descriptions,
        )
        stage = "解释模型请求"
        handler = LLMHandler(
            model_name,
            system_prompt=SYSTEM_PROMPT,
            enable_tools=use_agent.result,
            show_thinking=False,
        )
        logger.info(
            "解释模式调用模型（会话={}，模型={}，直传图片={}，外部资源={}）",
            handler.log_id,
            model_name,
            len(final_images or []),
            len(resources),
        )
        completion = await handler.ask(user_prompt, final_images)
        logger.info("解释模式模型调用完成（会话={}，模型={}）", handler.log_id, completion.model)
        stage = "响应解析"
        if vision_completion:
            completion.usage = vision_completion.usage + completion.usage
            completion.elapsed_seconds += vision_completion.elapsed_seconds
            completion.model = f"{vision_completion.model}→{completion.model}"
        content_text, _ = split_content(completion)
        completion.message.content = format_explain_response(content_text)
    except (ProviderError, ValueError) as e:
        logger.warning(
            "解释模式失败（会话={}，模型={}，阶段={}，错误类型={}，错误={}）",
            handler.log_id if handler else "-",
            model_name,
            stage,
            type(e).__name__,
            e,
        )
        await send_reaction("fail", message_id=msg_id)
        await UniMessage.text(f"解释失败：{e}").finish(reply_to=msg_id)
    except Exception as e:
        logger.opt(exception=e).error(
            "解释模式出现未预期的错误（会话={}，模型={}，阶段={}，错误类型={}）",
            handler.log_id if handler else "-",
            model_name,
            stage,
            type(e).__name__,
        )
        await send_reaction("fail", message_id=msg_id)
        await UniMessage.text("解释失败，请稍后重试").finish(reply_to=msg_id)
    else:
        await send_reaction("done", message_id=msg_id)
        await handler.send(completion, reply_to=msg_id)
