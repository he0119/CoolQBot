"""模型回复的格式化与发送

把一次提问的结果按配置发送给用户：生成的图片、推理内容、原生 Markdown、Markdown 图片或 TTS 语音，
以及处理开始和结束时的状态反馈。和请求模型的流程（`handler.py`）互不依赖。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from nonebot.log import logger
from nonebot_plugin_alconna import SupportAdapter, UniMessage, get_target, message_reaction

from .image_service import format_image_failure
from .tts import TTSError, text_to_speech

if TYPE_CHECKING:
    from .schemas import Completion, ImageContent, ImageResult

THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)
"""部分服务商把推理内容混在正文的 think 标签里"""

ReactionStatus = Literal["fail", "thinking", "done"]
REACTION_EMOJIS: dict[ReactionStatus, tuple[str, str]] = {
    "fail": ("10060", "❌"),
    "thinking": ("424", "👀"),
    "done": ("144", "🎉"),
}
"""OneBot V11 emoji ID 与其他平台 Unicode emoji 的对应关系"""

QQ_THINKING_NOTICE = "👀 已收到，正在处理……"
"""QQ 适配器不支持 reaction，开始处理时改发普通消息。"""


def split_content(completion: Completion) -> tuple[str, str]:
    """拆分模型回复为 (正文, 推理内容)

    Anthropic 的 thinking 块与 OpenAI 的 reasoning_content 已由 provider
    归一化到 `reasoning`；此处再兜底处理混在正文里的 think 标签。
    """
    content = completion.content
    reasoning = completion.reasoning

    if not reasoning:
        blocks = THINK_PATTERN.findall(content)
        reasoning = "\n".join(block.strip() for block in blocks if block.strip())

    return THINK_PATTERN.sub("", content).strip(), reasoning


def format_statistics(completion: Completion) -> str:
    """把本次提问的模型链、耗时及 token 用量格式化为尾注"""
    usage = completion.usage
    model = completion.model or "unknown"
    models = [part.strip() for part in model.split("→") if part.strip()] or ["unknown"]
    model_lines = [f"模型　{models[0]}"]
    model_lines.extend(f"　　　↳ {part}" for part in models[1:])
    model_text = "  \n".join(model_lines)
    return (
        "---\n"
        f"{model_text}  \n"
        f"统计　{completion.elapsed_seconds:.1f}s · "
        f"输入 {usage.input_tokens:,} · 输出 {usage.output_tokens:,} · "
        f"缓存 {usage.cache_read_tokens:,} · 共 {usage.total_tokens:,}"
    )


def format_thinking(reasoning: str) -> str:
    """把推理内容格式化为 Markdown 引用块"""
    return "\n".join(f"> {line}" if line else ">" for line in reasoning.splitlines())


def format_output(completion: Completion, *, with_thinking: bool, with_statistics: bool = True) -> str:
    """把模型回复格式化为最终文本"""
    content, reasoning = split_content(completion)
    if with_thinking and reasoning:
        thinking = format_thinking(reasoning)
        text = f"{thinking}\n\n{content}" if content else thinking
    else:
        text = content

    if text and with_statistics:
        return f"{text}\n\n{format_statistics(completion)}"
    return text


async def send_reaction(
    status: ReactionStatus,
    *,
    message_id: str | None = None,
) -> None:
    """反馈响应状态；QQ 开始处理时发消息，其余平台优先使用 reaction。"""
    try:
        target = get_target()
        if target.adapter == SupportAdapter.qq:
            if status == "thinking":
                await UniMessage.text(QQ_THINKING_NOTICE).send(reply_to=message_id or True)
            return

        is_onebot = target.adapter == SupportAdapter.onebot11
        if is_onebot and target.private:
            return

        emoji = REACTION_EMOJIS[status][0 if is_onebot else 1]
        await message_reaction(emoji, message_id=message_id)
    except Exception as e:
        logger.opt(exception=e).debug("发送大模型响应状态失败，已忽略")


async def _send_images(images: list[ImageContent], *, reply_to: str | bool) -> None:
    for image in images:
        await UniMessage.image(raw=image.data).send(reply_to=reply_to)


async def send_image_result(result: ImageResult, *, reply_to: str | bool = False) -> None:
    await _send_images(result.images, reply_to=reply_to)
    await UniMessage.text(result.summary()).send(reply_to=reply_to)


@dataclass
class ReplySender:
    """按配置把模型回复发送给用户"""

    send_markdown: bool = False
    """在支持的平台优先发送原生 Markdown"""
    send_md_pic: bool = False
    """把回复渲染成图片发送"""
    tts_model: str = ""
    """TTS 模型名，非空时用语音回复"""
    show_thinking: bool = False
    """是否附带推理内容"""
    log_id: str = "-"
    """用于关联日志的会话短 ID"""

    async def send(self, completion: Completion, *, reply_to: str | bool = False) -> None:
        """按配置发送模型回复"""
        await _send_images(completion.images, reply_to=reply_to)
        if completion.image_result is not None:
            await UniMessage.text(completion.image_result.summary()).send(reply_to=reply_to)
        elif completion.image_error is not None:
            await UniMessage.text(format_image_failure(completion.image_error)).send(reply_to=reply_to)
        text = format_output(completion, with_thinking=self.show_thinking)
        if not text:
            if completion.images:
                await UniMessage.text(format_statistics(completion)).send(reply_to=reply_to)
                return
            logger.warning("LLM 会话没有可发送内容（会话={}）", self.log_id)
            await UniMessage.text("模型没有返回任何内容").send(reply_to=reply_to)
            return

        if self.tts_model and await self._send_speech(completion, text, reply_to=reply_to):
            return

        if self.send_markdown and await try_send_markdown(text, reply_to=reply_to):
            logger.info("LLM 会话发送回复（会话={}，方式=原生 Markdown，字符={}）", self.log_id, len(text))
            return

        if self.send_md_pic and (image := await try_render_markdown(text)):
            logger.info("LLM 会话发送回复（会话={}，方式=Markdown 图片，图片字节={}）", self.log_id, len(image))
            await UniMessage.image(raw=image).send(reply_to=reply_to)
            return

        logger.info("LLM 会话发送回复（会话={}，方式=文本，字符={}）", self.log_id, len(text))
        await UniMessage.text(text).send(reply_to=reply_to)

    async def _send_speech(self, completion: Completion, text: str, *, reply_to: str | bool) -> bool:
        """发送语音回复；合成失败时提示并返回 False，由调用方改发文字。"""
        # 语音回复不朗读推理内容
        spoken = format_output(completion, with_thinking=False, with_statistics=False) or text
        try:
            audio = await text_to_speech(spoken, self.tts_model)
        except TTSError as e:
            logger.warning("LLM 会话语音合成失败，改用文字回复（会话={}）", self.log_id)
            await UniMessage.text(f"语音合成失败（{e}），以下是文字回复：").send(reply_to=reply_to)
            return False
        logger.info("LLM 会话发送回复（会话={}，方式=语音，音频字节={}）", self.log_id, len(audio))
        await UniMessage.audio(raw=audio).send(reply_to=reply_to)
        await UniMessage.text(format_statistics(completion)).send(reply_to=reply_to)
        return True


async def try_send_markdown(text: str, *, reply_to: str | bool = False) -> bool:
    """在支持的平台发送原生 Markdown，无法发送时返回 False 以便继续回退。"""
    try:
        adapter = get_target().adapter
    except Exception as e:
        logger.opt(exception=e).debug("无法判断当前平台的 Markdown 支持情况，继续使用回退格式")
        return False

    if adapter != SupportAdapter.qq:
        return False

    try:
        await UniMessage.style(text, "markdown").send(reply_to=reply_to)
    except Exception as e:
        logger.opt(exception=e).warning("原生 Markdown 回复发送失败，继续使用回退格式")
        return False
    return True


async def try_render_markdown(text: str) -> bytes | None:
    """把 Markdown 渲染成图片，失败时返回 None 以便退回文字

    htmlrender 依赖浏览器环境，导入与渲染都可能失败，因此一并兜底。
    """
    try:
        from nonebot_plugin_htmlrender import render_markdown

        return await render_markdown(text)
    except Exception as e:
        logger.opt(exception=e).warning("Markdown 渲染图片失败，改用文字回复")
        return None
