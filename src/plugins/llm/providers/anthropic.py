"""Anthropic Messages 格式

请求：`POST {base_url}/v1/messages`
认证：`x-api-key` 请求头 + `anthropic-version`，而非 Bearer
消息：`messages` 数组，system 提示词由顶层 `system` 承载
内容：一律为内容块数组，`text` / `thinking` / `tool_use` / `tool_result` / `image`
工具：`tools[].{name,description,input_schema}`，注意是 `input_schema`
工具结果：作为 `tool_result` 块放在 **user** 消息里，而非独立的 tool 角色
图片：`source.{type:base64,media_type,data}`，纯 base64 不带 data URI 前缀
用量：`input_tokens` / `output_tokens` + `cache_creation_input_tokens` / `cache_read_input_tokens`
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from ..schemas import Completion, Message, ToolCall, Usage
from .base import Provider, iter_sse

if TYPE_CHECKING:
    import httpx

    from ..schemas import ToolChoice, ToolParam

ANTHROPIC_VERSION = "2023-06-01"
"""Anthropic API 版本，通过 anthropic-version 请求头发送"""

DEFAULT_MAX_TOKENS = 4096
"""Anthropic 要求必须提供 max_tokens，未配置时使用此默认值"""


class AnthropicProvider(Provider):
    """Anthropic Messages 客户端"""

    @property
    def endpoint(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/v1/messages"

    def build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }

    def build_payload(
        self,
        messages: list[Message],
        tools: list[ToolParam] | None = None,
        stream: bool = False,
        tool_choice: ToolChoice = "auto",
    ) -> dict[str, Any]:
        system_parts = [m.content for m in messages if m.role == "system" and m.content]
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": self._dump_messages([m for m in messages if m.role != "system"]),
            "max_tokens": self.config.max_tokens or DEFAULT_MAX_TOKENS,
            "stream": stream,
        }
        if system_parts:
            payload["system"] = "\n".join(system_parts)
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        if tools:
            payload["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in tools
            ]
        payload.update(self.config.extra_body)
        if tools and tool_choice == "none":
            payload["tool_choice"] = {"type": "none"}
        return payload

    def _dump_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """转换消息列表

        tool 角色在 Anthropic 中不存在，需要折叠成 user 消息里的 tool_result 块；
        连续的多个工具结果还要合并进同一条 user 消息。
        """
        dumped: list[dict[str, Any]] = []

        for message in messages:
            if message.role == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": message.tool_call_id,
                    "content": message.content,
                }
                # 紧跟在上一条工具结果后面时合并，避免出现连续的 user 消息
                if dumped and dumped[-1]["role"] == "user" and _is_tool_result(dumped[-1]):
                    dumped[-1]["content"].append(block)
                else:
                    dumped.append({"role": "user", "content": [block]})
                continue

            content: list[dict[str, Any]] = []
            if message.role == "user":
                content.extend(
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": i.mimetype, "data": i.to_base64()},
                    }
                    for i in message.images
                )
                if message.content:
                    content.append({"type": "text", "text": message.content})
            else:
                if raw_content := message.provider_data.get("anthropic_content"):
                    content = copy.deepcopy(raw_content)
                else:
                    if message.content:
                        content.append({"type": "text", "text": message.content})
                    content.extend(
                        {
                            "type": "tool_use",
                            "id": call.id,
                            "name": call.name,
                            "input": call.arguments,
                        }
                        for call in message.tool_calls
                    )

            if content:
                dumped.append({"role": message.role, "content": content})

        return dumped

    def parse_response(self, data: dict[str, Any]) -> Completion:
        text: list[str] = []
        thinking: list[str] = []
        tool_calls: list[ToolCall] = []

        raw_content = data.get("content") or []
        for block in raw_content:
            block_type = block.get("type")
            if block_type == "text":
                text.append(block.get("text") or "")
            elif block_type == "thinking":
                thinking.append(block.get("thinking") or "")
            elif block_type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id") or "",
                        name=block.get("name") or "",
                        arguments=block.get("input") or {},
                    )
                )

        return Completion(
            message=Message.assistant(
                content="".join(text),
                reasoning="".join(thinking),
                tool_calls=tool_calls,
                provider_data={"anthropic_content": copy.deepcopy(raw_content)},
            ),
            usage=self._parse_usage(data.get("usage")),
            model=data.get("model", ""),
            finish_reason=_finish_reason(data.get("stop_reason")),
        )

    async def parse_stream(self, response: httpx.Response) -> Completion:
        text: list[str] = []
        thinking: list[str] = []
        # 内容块按 index 到达，tool_use 的入参以 JSON 字符串分片累积
        blocks: dict[int, dict[str, Any]] = {}
        partial_json: dict[int, str] = {}
        usage = Usage()
        model = ""
        stop_reason = ""

        async for event, data in iter_sse(response):
            if event == "error" or data.get("type") == "error":
                self.raise_for_error(data)

            event = event or data.get("type") or ""

            if event == "message_start":
                message = data.get("message") or {}
                model = message.get("model") or model
                usage = self._parse_usage(message.get("usage"))
            elif event == "content_block_start":
                index = data.get("index", 0)
                block = copy.deepcopy(data.get("content_block") or {})
                blocks[index] = block
                if block.get("type") == "tool_use":
                    partial_json[index] = ""
            elif event == "content_block_delta":
                index = data.get("index", 0)
                delta = data.get("delta") or {}
                delta_type = delta.get("type")
                if delta_type == "text_delta":
                    chunk = delta.get("text") or ""
                    text.append(chunk)
                    block = blocks.setdefault(index, {"type": "text", "text": ""})
                    block["text"] = (block.get("text") or "") + chunk
                elif delta_type == "thinking_delta":
                    chunk = delta.get("thinking") or ""
                    thinking.append(chunk)
                    block = blocks.setdefault(index, {"type": "thinking", "thinking": ""})
                    block["thinking"] = (block.get("thinking") or "") + chunk
                elif delta_type == "signature_delta":
                    block = blocks.setdefault(index, {"type": "thinking", "thinking": ""})
                    block["signature"] = (block.get("signature") or "") + (delta.get("signature") or "")
                elif delta_type == "input_json_delta":
                    partial_json[index] = partial_json.get(index, "") + (delta.get("partial_json") or "")
            elif event == "content_block_stop":
                index = data.get("index", 0)
                if index in partial_json and (block := blocks.get(index)) is not None:
                    block["input"] = _loads(partial_json[index])
            elif event == "message_delta":
                stop_reason = (data.get("delta") or {}).get("stop_reason") or stop_reason
                # message_delta 只带增量的 output_tokens，需要并入已有用量
                if raw_usage := data.get("usage"):
                    delta_usage = self._parse_usage(raw_usage)
                    usage.output_tokens = delta_usage.output_tokens or usage.output_tokens
                    usage.input_tokens = delta_usage.input_tokens or usage.input_tokens

        for index, raw in partial_json.items():
            if (block := blocks.get(index)) is not None:
                block["input"] = _loads(raw)

        raw_content = [block for _, block in sorted(blocks.items())]
        tool_calls = [
            ToolCall(
                id=block.get("id") or "",
                name=block.get("name") or "",
                arguments=block.get("input") or {},
            )
            for block in raw_content
            if block.get("type") == "tool_use" and block.get("name")
        ]
        return Completion(
            message=Message.assistant(
                content="".join(text),
                reasoning="".join(thinking),
                tool_calls=tool_calls,
                provider_data={"anthropic_content": raw_content},
            ),
            usage=usage,
            model=model,
            finish_reason=_finish_reason(stop_reason),
        )

    def _parse_usage(self, raw: dict[str, Any] | None) -> Usage:
        if not raw:
            return Usage()
        return Usage(
            input_tokens=raw.get("input_tokens") or 0,
            output_tokens=raw.get("output_tokens") or 0,
            cache_read_tokens=raw.get("cache_read_input_tokens") or 0,
            cache_write_tokens=raw.get("cache_creation_input_tokens") or 0,
        )


def _is_tool_result(message: dict[str, Any]) -> bool:
    """判断一条已转换的消息是否由工具结果块组成"""
    content = message.get("content")
    return isinstance(content, list) and bool(content) and content[-1].get("type") == "tool_result"


def _finish_reason(stop_reason: str | None) -> str:
    """把 Anthropic 的 stop_reason 归一化为与 Chat Completions 一致的取值"""
    mapping = {
        "end_turn": "stop",
        "stop_sequence": "stop",
        "max_tokens": "length",
        "tool_use": "tool_calls",
        "refusal": "content_filter",
    }
    return mapping.get(stop_reason or "", stop_reason or "")


def _loads(raw: str) -> dict[str, Any]:
    import json

    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
