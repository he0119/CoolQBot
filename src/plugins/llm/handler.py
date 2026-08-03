"""大模型对话处理

负责组装上下文、驱动多轮对话、执行工具调用，并按配置决定回复形式
（文本 / Markdown 图片 / TTS 语音）。
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from nonebot.log import logger
from nonebot_plugin_alconna import SupportAdapter, UniMessage, get_target, message_reaction

from .config import plugin_config
from .providers import ProviderError, get_provider
from .schemas import Completion, ImageContent, Message
from .tools import registry
from .tts import TTSError, text_to_speech

if TYPE_CHECKING:
    from .schemas import ToolCall

THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)
"""部分服务商把推理内容混在正文的 think 标签里"""

TOOL_ROUND_LIMIT_PROMPT = (
    "工具调用轮数已达到上限。请停止调用工具，仅根据已经获取的信息直接回答用户；如果信息不足，请明确说明尚未完成的部分。"
)
"""工具调用达到上限后用于强制生成收尾回复的临时提示词。"""

ReactionStatus = Literal["fail", "thinking", "done"]
ToolWaitNotifier = Callable[[int, int, int], Awaitable[None]]
REACTION_EMOJIS: dict[ReactionStatus, tuple[str, str]] = {
    "fail": ("10060", "❌"),
    "thinking": ("424", "👀"),
    "done": ("144", "🎉"),
}
"""QQ emoji ID 与其他平台 Unicode emoji 的对应关系"""


@dataclass
class _ToolWaitProgress:
    """等待提示使用的非敏感工具调用进度。"""

    request_count: int = 1
    tool_call_count: int = 0


async def chat(
    model_name: str,
    messages: list[Message],
    *,
    session_affinity: str = "",
    enable_tools: bool = True,
) -> Completion:
    """发起一次对话请求"""
    model = plugin_config.resolve(model_name)
    provider = get_provider(model.provider)(model, session_affinity=session_affinity)
    tools = registry.to_params() if enable_tools else []
    return await provider.chat(messages, tools or None)


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
    """把本次提问的耗时、模型及 token 用量格式化为紧凑尾注"""
    usage = completion.usage
    model = completion.model or "unknown"
    return (
        f"--- {completion.elapsed_seconds:.1f}s  "
        f"{model}  I:{usage.input_tokens} O:{usage.output_tokens} "
        f"A:{usage.total_tokens} C:{usage.cache_read_tokens}"
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
    """给触发消息添加响应状态；平台不支持或调用失败时静默跳过"""
    try:
        target = get_target()
        is_qq = target.adapter in (SupportAdapter.onebot11, SupportAdapter.qq)
        if is_qq and target.private:
            return

        emoji = REACTION_EMOJIS[status][0 if is_qq else 1]
        await message_reaction(emoji, message_id=message_id)
    except Exception as e:
        logger.opt(exception=e).debug("添加大模型响应状态失败，已忽略")


async def execute_tool_calls(calls: list[ToolCall], context: list[Message]) -> None:
    """并行执行模型请求的工具调用，并按原顺序把结果加入上下文"""
    results = await asyncio.gather(*(registry.execute(call) for call in calls))
    context.extend(Message.tool(call.id, result) for call, result in zip(calls, results, strict=True))


class LLMHandler:
    """一次提问的处理流程"""

    def __init__(
        self,
        model_name: str,
        *,
        session_affinity: str | None = None,
        send_md_pic: bool = False,
        tts_model: str = "",
        system_prompt: str | None = None,
        enable_tools: bool = True,
        show_thinking: bool | None = None,
    ) -> None:
        self.model_name = model_name
        self.session_affinity = session_affinity or uuid4().hex
        self.send_md_pic = send_md_pic
        self.tts_model = tts_model
        self.enable_tools = enable_tools
        self.show_thinking = plugin_config.send_thinking if show_thinking is None else show_thinking
        self.context: list[Message] = []

        prompt = plugin_config.resolve(model_name).prompt if system_prompt is None else system_prompt
        if prompt:
            self.context.append(Message(role="system", content=prompt))

    @property
    def log_id(self) -> str:
        """用于关联日志的随机短 ID，不包含用户或群组信息。"""
        return self.session_affinity[:8]

    async def ask(
        self,
        content: str,
        images: list[ImageContent] | None = None,
        *,
        on_tool_wait: ToolWaitNotifier | None = None,
    ) -> Completion:
        """追加一轮用户输入并请求模型

        模型请求工具调用时自动执行并继续请求，直到给出最终回复；
        达到 `max_tool_rounds` 轮数上限后禁用工具生成收尾回复。
        """
        if images and "vision" not in plugin_config.get_model(self.model_name).capabilities:
            raise ValueError(f"模型 {self.model_name} 未声明 vision 能力，不能接收图片")

        context_start = len(self.context)
        self.context.append(Message.user(content, images))

        started_at = perf_counter()
        logger.info(
            "LLM 会话开始请求（会话={}，模型={}，上下文消息={}，输入字符={}，图片={}，工具={}）",
            self.log_id,
            self.model_name,
            context_start,
            len(content),
            len(images or []),
            "启用" if self.enable_tools else "禁用",
        )
        completion = await chat(
            self.model_name,
            self.context,
            session_affinity=self.session_affinity,
            enable_tools=self.enable_tools,
        )
        if completion.tool_calls and not self.enable_tools:
            del self.context[context_start:]
            logger.warning(
                "LLM 会话拒绝工具调用（会话={}，调用数量={}）",
                self.log_id,
                len(completion.tool_calls),
            )
            raise ProviderError("当前模式不允许工具调用")
        total_usage = completion.usage
        actual_model = completion.model
        tool_rounds = 0
        notice_task: asyncio.Task[None] | None = None
        tool_progress = _ToolWaitProgress()
        try:
            for tool_round in range(1, plugin_config.max_tool_rounds + 1):
                if not completion.tool_calls:
                    break
                tool_progress.tool_call_count += len(completion.tool_calls)
                if on_tool_wait and notice_task is None:
                    notice_task = asyncio.create_task(self._send_tool_wait_notices(on_tool_wait, tool_progress))
                tool_rounds = tool_round
                logger.info(
                    "LLM 会话执行工具回合（会话={}，轮次={}，调用数量={}）",
                    self.log_id,
                    tool_round,
                    len(completion.tool_calls),
                )
                self.context.append(completion.message)
                await execute_tool_calls(completion.tool_calls, self.context)
                tool_progress.request_count += 1
                completion = await chat(
                    self.model_name,
                    self.context,
                    session_affinity=self.session_affinity,
                    enable_tools=self.enable_tools,
                )
                total_usage = total_usage + completion.usage
                actual_model = completion.model or actual_model

            if completion.tool_calls:
                logger.warning(
                    "LLM 会话工具调用达到上限，转为无工具收尾（会话={}，上限={}，未执行调用={}）",
                    self.log_id,
                    plugin_config.max_tool_rounds,
                    len(completion.tool_calls),
                )
                final_context = list(self.context)
                first_non_system = next(
                    (index for index, message in enumerate(final_context) if message.role != "system"),
                    len(final_context),
                )
                final_context.insert(first_non_system, Message(role="system", content=TOOL_ROUND_LIMIT_PROMPT))
                tool_progress.request_count += 1
                try:
                    completion = await chat(
                        self.model_name,
                        final_context,
                        session_affinity=self.session_affinity,
                        enable_tools=False,
                    )
                except Exception:
                    del self.context[context_start:]
                    raise
                total_usage = total_usage + completion.usage
                actual_model = completion.model or actual_model
        finally:
            if notice_task:
                notice_task.cancel()
                with suppress(asyncio.CancelledError):
                    await notice_task

        if completion.tool_calls:
            del self.context[context_start:]
            logger.warning(
                "LLM 会话无工具收尾仍返回工具调用（会话={}，上限={}，调用数量={}）",
                self.log_id,
                plugin_config.max_tool_rounds,
                len(completion.tool_calls),
            )
            raise ProviderError(f"工具调用达到上限后仍未生成最终回复（{plugin_config.max_tool_rounds} 轮）")

        completion.usage = total_usage
        completion.model = actual_model or plugin_config.resolve(self.model_name).model
        completion.elapsed_seconds = perf_counter() - started_at
        self.context.append(completion.message)
        logger.info(
            "LLM 会话请求完成（会话={}，模型={}，结束原因={}，工具轮次={}，I={}，O={}，C={}，耗时={:.3f}s）",
            self.log_id,
            completion.model,
            completion.finish_reason,
            tool_rounds,
            completion.usage.input_tokens,
            completion.usage.output_tokens,
            completion.usage.cache_read_tokens,
            completion.elapsed_seconds,
        )
        return completion

    async def _send_tool_wait_notices(self, notify: ToolWaitNotifier, progress: _ToolWaitProgress) -> None:
        """工具阶段未完成时按配置周期发送等待提示。"""
        delay = plugin_config.tool_notice_delay
        count = 0
        while True:
            await asyncio.sleep(delay)
            count += 1
            try:
                await notify(count, progress.request_count, progress.tool_call_count)
            except Exception as e:
                logger.opt(exception=e).debug(
                    "LLM 工具等待提示发送失败，已忽略（会话={}，次数={}，模型请求={}，工具调用={}）",
                    self.log_id,
                    count,
                    progress.request_count,
                    progress.tool_call_count,
                )
            else:
                logger.info(
                    "LLM 会话发送工具等待提示（会话={}，次数={}，模型请求={}，工具调用={}）",
                    self.log_id,
                    count,
                    progress.request_count,
                    progress.tool_call_count,
                )
            delay = plugin_config.tool_notice_interval

    def rollback(self) -> bool:
        """回滚最近一轮对话，成功时返回 True"""
        # 一轮 = 一条用户输入 + 一条模型回复，工具消息也一并回滚
        removed_count = 0
        while self.context and self.context[-1].role != "user":
            self.context.pop()
            removed_count += 1
        if self.context and self.context[-1].role == "user":
            self.context.pop()
            removed_count += 1
        if removed_count:
            logger.info("LLM 会话已回滚（会话={}，移除消息={}）", self.log_id, removed_count)
        return bool(removed_count)

    async def send(
        self,
        completion: Completion,
        *,
        reply_to: str | bool = False,
    ) -> None:
        """按配置发送模型回复"""
        text = format_output(completion, with_thinking=self.show_thinking)
        if not text:
            logger.warning("LLM 会话没有可发送内容（会话={}）", self.log_id)
            await UniMessage.text("模型没有返回任何内容").send(reply_to=reply_to)
            return

        if self.tts_model:
            # 语音回复不朗读推理内容
            spoken = format_output(completion, with_thinking=False, with_statistics=False) or text
            try:
                audio = await text_to_speech(spoken, self.tts_model)
            except TTSError as e:
                logger.warning("LLM 会话语音合成失败，改用文字回复（会话={}）", self.log_id)
                await UniMessage.text(f"语音合成失败（{e}），以下是文字回复：").send(reply_to=reply_to)
            else:
                logger.info(
                    "LLM 会话发送回复（会话={}，方式=语音，音频字节={}）",
                    self.log_id,
                    len(audio),
                )
                await UniMessage.audio(raw=audio).send(reply_to=reply_to)
                await UniMessage.text(format_statistics(completion)).send(reply_to=reply_to)
                return

        if self.send_md_pic:
            if image := await try_render_markdown(text):
                logger.info(
                    "LLM 会话发送回复（会话={}，方式=Markdown 图片，图片字节={}）",
                    self.log_id,
                    len(image),
                )
                await UniMessage.image(raw=image).send(reply_to=reply_to)
                return

        logger.info("LLM 会话发送回复（会话={}，方式=文本，字符={}）", self.log_id, len(text))
        await UniMessage.text(text).send(reply_to=reply_to)


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
