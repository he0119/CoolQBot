"""大模型对话处理

负责组装上下文、驱动多轮对话、执行工具调用，并按配置决定回复形式
（文本 / Markdown 图片 / TTS 语音）。
"""

from __future__ import annotations

import asyncio
import re
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import uuid4

from nonebot.log import logger
from nonebot_plugin_alconna import UniMessage

from .config import plugin_config
from .providers import ProviderError, get_provider
from .schemas import Completion, ImageContent, Message
from .tools import registry
from .tts import TTSError, text_to_speech

if TYPE_CHECKING:
    from .schemas import ToolCall

THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)
"""部分服务商把推理内容混在正文的 think 标签里"""

THINKING_SEPARATOR = "\n\n--------------------\n\n"
"""推理内容与正文之间的分隔线"""


async def chat(model_name: str, messages: list[Message], *, session_affinity: str = "") -> Completion:
    """发起一次对话请求"""
    model = plugin_config.resolve(model_name)
    provider = get_provider(model.provider)(model, session_affinity=session_affinity)
    tools = registry.to_params()
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


def format_output(completion: Completion, *, with_thinking: bool, with_statistics: bool = True) -> str:
    """把模型回复格式化为最终文本"""
    content, reasoning = split_content(completion)
    if with_thinking and reasoning:
        text = f"{reasoning}{THINKING_SEPARATOR}{content}" if content else reasoning
    else:
        text = content

    if text and with_statistics:
        return f"{text}\n\n{format_statistics(completion)}"
    return text


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
    ) -> None:
        self.model_name = model_name
        self.session_affinity = session_affinity or uuid4().hex
        self.send_md_pic = send_md_pic
        self.tts_model = tts_model
        self.context: list[Message] = []

        prompt = plugin_config.resolve(model_name).prompt
        if prompt:
            self.context.append(Message(role="system", content=prompt))

    async def ask(self, content: str, images: list[ImageContent] | None = None) -> Completion:
        """追加一轮用户输入并请求模型

        模型请求工具调用时自动执行并继续请求，直到给出最终回复
        或达到 `max_tool_rounds` 轮数上限。
        """
        context_start = len(self.context)
        self.context.append(Message.user(content, images))

        started_at = perf_counter()
        completion = await chat(self.model_name, self.context, session_affinity=self.session_affinity)
        total_usage = completion.usage
        actual_model = completion.model
        for _ in range(plugin_config.max_tool_rounds):
            if not completion.tool_calls:
                break
            self.context.append(completion.message)
            await execute_tool_calls(completion.tool_calls, self.context)
            completion = await chat(self.model_name, self.context, session_affinity=self.session_affinity)
            total_usage = total_usage + completion.usage
            actual_model = completion.model or actual_model

        if completion.tool_calls:
            del self.context[context_start:]
            raise ProviderError(f"工具调用超过上限（{plugin_config.max_tool_rounds} 轮）")

        completion.usage = total_usage
        completion.model = actual_model or plugin_config.resolve(self.model_name).model
        completion.elapsed_seconds = perf_counter() - started_at
        self.context.append(completion.message)
        return completion

    def rollback(self) -> bool:
        """回滚最近一轮对话，成功时返回 True"""
        # 一轮 = 一条用户输入 + 一条模型回复，工具消息也一并回滚
        removed = False
        while self.context and self.context[-1].role != "user":
            self.context.pop()
            removed = True
        if self.context and self.context[-1].role == "user":
            self.context.pop()
            removed = True
        return removed

    async def send(self, completion: Completion) -> None:
        """按配置发送模型回复"""
        text = format_output(completion, with_thinking=plugin_config.send_thinking)
        if not text:
            await UniMessage.text("模型没有返回任何内容").send()
            return

        if self.tts_model:
            # 语音回复不朗读推理内容
            spoken = format_output(completion, with_thinking=False, with_statistics=False) or text
            try:
                audio = await text_to_speech(spoken, self.tts_model)
            except TTSError as e:
                logger.opt(exception=e).warning("语音合成失败，改用文字回复")
                await UniMessage.text(f"语音合成失败（{e}），以下是文字回复：").send()
            else:
                await UniMessage.audio(raw=audio).send()
                await UniMessage.text(format_statistics(completion)).send()
                return

        if self.send_md_pic:
            if image := await try_render_markdown(text):
                await UniMessage.image(raw=image).send()
                return

        await UniMessage.text(text).send()


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
