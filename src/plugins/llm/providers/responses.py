"""OpenAI Responses 格式

请求：`POST {base_url}/responses`
消息：`input` 数组，system 提示词由顶层 `instructions` 承载
工具：`tools[].{name,description,parameters}`（扁平结构，无 function 嵌套）
图片：`input` 中的 `input_image` 项，值为 data URI
用量：`input_tokens` / `output_tokens`
"""

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING, Any

from ..schemas import Completion, Message, ToolCall, Usage
from .base import Provider, ProviderError, iter_sse

if TYPE_CHECKING:
    import httpx

    from ..schemas import ToolParam


class ResponsesProvider(Provider):
    """OpenAI Responses 客户端"""

    @property
    def endpoint(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/responses"

    def build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

    def build_payload(
        self,
        messages: list[Message],
        tools: list[ToolParam] | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": self.config.model, "stream": stream}
        if self.config.max_tokens:
            payload["max_output_tokens"] = self.config.max_tokens
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature

        system_parts: list[str] = []
        input_items: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                if message.content:
                    system_parts.append(message.content)
                continue
            input_items.extend(self._dump_items(message))
        if system_parts:
            payload["instructions"] = "\n".join(system_parts)
        if input_items:
            payload["input"] = input_items
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
                for tool in tools
            ]
        payload.update(self.config.extra_body)
        return payload

    def _dump_items(self, message: Message) -> list[dict[str, Any]]:
        if message.role == "tool":
            return [{"type": "function_call_output", "call_id": message.tool_call_id, "output": message.content}]

        if message.role == "assistant":
            if raw_output := message.provider_data.get("responses_output"):
                return copy.deepcopy(raw_output)

            output: list[dict[str, Any]] = []
            if message.content:
                output.append(
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": message.content}],
                    }
                )
            for call in message.tool_calls:
                output.append(
                    {
                        "type": "function_call",
                        "call_id": call.id,
                        "name": call.name,
                        "arguments": call.arguments_json(),
                    }
                )
            return output

        # user 消息
        content: list[dict[str, Any]] = []
        if message.content:
            content.append({"type": "input_text", "text": message.content})
        content.extend({"type": "input_image", "image_url": i.to_data_uri()} for i in message.images)
        return [{"type": "message", "role": "user", "content": content}]

    def parse_response(self, data: dict[str, Any]) -> Completion:
        output_items = data.get("output") or []
        message = self._extract_message(output_items)
        return Completion(
            message=message,
            usage=self._parse_usage(data.get("usage")),
            model=data.get("model", ""),
            finish_reason="tool_calls" if message.tool_calls else _finish_reason(data),
        )

    async def parse_stream(self, response: httpx.Response) -> Completion:
        content: list[str] = []
        reasoning: list[str] = []
        # 工具调用以 item_id 为键，name 由 output_item.added 给出，
        # arguments 以 JSON 字符串分片到达，先按片累积、结束时统一解析
        names: dict[str, str] = {}
        call_ids: dict[str, str] = {}
        arguments: dict[str, str] = {}
        order: list[str] = []
        raw_output: dict[int, dict[str, Any]] = {}
        usage = Usage()
        model = ""
        finish_reason = ""

        async for event, data in iter_sse(response):
            if event == "error" or data.get("type") == "error":
                self.raise_for_error(data, 500)
            if event == "response.failed":
                response_data = data.get("response") or {}
                error = response_data.get("error") or data.get("error")
                if error:
                    self.raise_for_error({"error": error})
                raise ProviderError("响应生成失败")
            self.raise_for_error(data)

            if event in ("response.created", "response.completed", "response.incomplete"):
                response_data = data.get("response") or {}
                model = response_data.get("model") or model
                finish_reason = _finish_reason(response_data) or finish_reason
                if raw_usage := response_data.get("usage"):
                    usage = self._parse_usage(raw_usage)
            elif event == "response.output_text.delta":
                content.append(data.get("delta") or "")
            elif event in ("response.reasoning_summary_text.delta", "response.reasoning_text.delta"):
                reasoning.append(data.get("delta") or "")
            elif event in ("response.output_item.added", "response.output_item.done"):
                item = copy.deepcopy(data.get("item") or {})
                output_index = data.get("output_index")
                if not isinstance(output_index, int):
                    output_index = len(raw_output)
                raw_output[output_index] = item
                if item.get("type") == "function_call":
                    item_id = item.get("id") or item.get("call_id") or ""
                    if item_id not in order:
                        order.append(item_id)
                    names[item_id] = item.get("name") or ""
                    call_ids[item_id] = item.get("call_id") or item_id
                    if item.get("arguments") is not None:
                        arguments[item_id] = item["arguments"]
            elif event == "response.function_call_arguments.delta":
                item_id = data.get("item_id") or ""
                if item_id not in order:
                    order.append(item_id)
                arguments[item_id] = arguments.get(item_id, "") + (data.get("delta") or "")
            elif event == "response.function_call_arguments.done":
                item_id = data.get("item_id") or ""
                if item_id not in order:
                    order.append(item_id)
                # done 事件带的是完整参数，直接覆盖累积结果
                if (full := data.get("arguments")) is not None:
                    arguments[item_id] = full

        tool_calls = [
            ToolCall(
                id=call_ids.get(item_id, item_id),
                name=names.get(item_id, ""),
                arguments=_loads(arguments.get(item_id)),
            )
            for item_id in order
            if names.get(item_id)
        ]
        return Completion(
            message=Message.assistant(
                content="".join(content),
                reasoning="".join(reasoning),
                tool_calls=tool_calls,
                provider_data={"responses_output": [item for _, item in sorted(raw_output.items())]},
            ),
            usage=usage,
            model=model,
            finish_reason="tool_calls" if tool_calls else finish_reason,
        )

    def _extract_message(self, output_items: list[dict[str, Any]]) -> Message:
        text: list[str] = []
        reasoning: list[str] = []
        tool_calls: list[ToolCall] = []

        for item in output_items:
            item_type = item.get("type")
            if item_type == "message":
                for part in item.get("content") or []:
                    if part.get("type") == "output_text":
                        text.append(part.get("text") or "")
            elif item_type == "reasoning":
                for part in item.get("summary") or []:
                    if part.get("type") == "summary_text":
                        reasoning.append(part.get("text") or "")
            elif item_type == "function_call":
                tool_calls.append(
                    ToolCall(
                        id=item.get("call_id") or item.get("id") or "",
                        name=item.get("name") or "",
                        arguments=_loads(item.get("arguments")),
                    )
                )

        return Message.assistant(
            content="".join(text),
            reasoning="\n".join(reasoning),
            tool_calls=tool_calls,
            provider_data={"responses_output": copy.deepcopy(output_items)},
        )

    def _parse_usage(self, raw: dict[str, Any] | None) -> Usage:
        if not raw:
            return Usage()
        output_details = raw.get("output_tokens_details") or {}
        input_details = raw.get("input_tokens_details") or {}
        return Usage(
            input_tokens=raw.get("input_tokens") or 0,
            output_tokens=raw.get("output_tokens") or 0,
            reasoning_tokens=output_details.get("reasoning_tokens") or 0,
            cache_read_tokens=input_details.get("cached_tokens") or 0,
        )


def _finish_reason(data: dict[str, Any]) -> str:
    """把 Responses 的状态归一化为与 Chat Completions 一致的结束原因"""
    if data.get("status") == "incomplete":
        reason = (data.get("incomplete_details") or {}).get("reason")
        return "length" if reason == "max_output_tokens" else str(reason or "")
    return "stop" if data.get("status") == "completed" else ""


def _loads(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
