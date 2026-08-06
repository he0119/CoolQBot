"""OpenAI Chat Completions 格式

请求：`POST {base_url}/chat/completions`
消息：`messages` 数组，system 也是一条消息
工具：`tools[].function.{name,description,parameters}`（嵌套）
图片：`content[].image_url.url`，值为 data URI
用量：`prompt_tokens` / `completion_tokens`
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..schemas import Completion, Message, ToolCall, Usage
from .base import Provider, iter_sse

if TYPE_CHECKING:
    import httpx

    from ..schemas import ToolChoice, ToolParam


class ChatProvider(Provider):
    """OpenAI Chat Completions 客户端"""

    @property
    def endpoint(self) -> str:
        return f"{self.config.base_url.rstrip('/')}/chat/completions"

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
        tool_choice: ToolChoice = "auto",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [self._dump_message(m) for m in messages],
            "stream": stream,
        }
        if self.config.max_tokens:
            payload["max_tokens"] = self.config.max_tokens
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        if stream:
            # 要求在最后一个数据块中带上用量统计
            payload["stream_options"] = {"include_usage": True}
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in tools
            ]
        payload.update(self.config.extra_body)
        if tools and tool_choice == "none":
            # 收尾请求必须覆盖模型级 extra_body，避免 required/auto 重新开启工具。
            payload["tool_choice"] = "none"
        return payload

    def _dump_message(self, message: Message) -> dict[str, Any]:
        if message.role == "tool":
            return {
                "role": "tool",
                "tool_call_id": message.tool_call_id,
                "content": message.content,
            }

        data: dict[str, Any] = {"role": message.role}

        if message.images:
            content: list[dict[str, Any]] = []
            if message.content:
                content.append({"type": "text", "text": message.content})
            content.extend({"type": "image_url", "image_url": {"url": i.to_data_uri()}} for i in message.images)
            data["content"] = content
        else:
            data["content"] = message.content

        if message.tool_calls:
            data["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments_json()},
                }
                for call in message.tool_calls
            ]
        if message.role == "assistant" and message.reasoning:
            data["reasoning_content"] = message.reasoning
        return data

    def parse_response(self, data: dict[str, Any]) -> Completion:
        choices = data.get("choices") or []
        if not choices:
            return Completion(message=Message.assistant(), model=data.get("model", ""))

        choice = choices[0]
        raw = choice.get("message") or {}
        return Completion(
            message=Message.assistant(
                content=raw.get("content") or "",
                reasoning=raw.get("reasoning_content") or raw.get("reasoning") or "",
                tool_calls=self._parse_tool_calls(raw.get("tool_calls")),
            ),
            usage=self._parse_usage(data.get("usage")),
            model=data.get("model", ""),
            finish_reason=choice.get("finish_reason") or "",
        )

    async def parse_stream(self, response: httpx.Response) -> Completion:
        content: list[str] = []
        reasoning: list[str] = []
        # 工具调用参数按 index 分片到达，需要按 index 累积拼接
        tool_chunks: dict[int, dict[str, str]] = {}
        usage = Usage()
        model = ""
        finish_reason = ""

        async for _, data in iter_sse(response):
            self.raise_for_error(data)
            model = data.get("model") or model
            if raw_usage := data.get("usage"):
                usage = self._parse_usage(raw_usage)

            for choice in data.get("choices") or []:
                finish_reason = choice.get("finish_reason") or finish_reason
                delta = choice.get("delta") or {}
                if text := delta.get("content"):
                    content.append(text)
                if think := delta.get("reasoning_content") or delta.get("reasoning"):
                    reasoning.append(think)

                for call in delta.get("tool_calls") or []:
                    index = call.get("index", 0)
                    chunk = tool_chunks.setdefault(index, {"id": "", "name": "", "arguments": ""})
                    if call_id := call.get("id"):
                        chunk["id"] = call_id
                    function = call.get("function") or {}
                    if name := function.get("name"):
                        chunk["name"] = name
                    if arguments := function.get("arguments"):
                        chunk["arguments"] += arguments

        tool_calls = self._parse_tool_calls(
            [
                {"id": chunk["id"], "function": {"name": chunk["name"], "arguments": chunk["arguments"]}}
                for _, chunk in sorted(tool_chunks.items())
            ]
        )
        return Completion(
            message=Message.assistant(
                content="".join(content),
                reasoning="".join(reasoning),
                tool_calls=tool_calls,
            ),
            usage=usage,
            model=model,
            finish_reason=finish_reason,
        )

    def _parse_tool_calls(self, raw: list[dict[str, Any]] | None) -> list[ToolCall]:
        if not raw:
            return []

        calls: list[ToolCall] = []
        for item in raw:
            function = item.get("function") or {}
            name = function.get("name")
            if not name:
                continue
            calls.append(
                ToolCall(
                    id=item.get("id") or "",
                    name=name,
                    arguments=_loads_arguments(function.get("arguments")),
                )
            )
        return calls

    def _parse_usage(self, raw: dict[str, Any] | None) -> Usage:
        if not raw:
            return Usage()

        completion_details = raw.get("completion_tokens_details") or {}
        prompt_details = raw.get("prompt_tokens_details") or {}
        return Usage(
            input_tokens=raw.get("prompt_tokens") or 0,
            output_tokens=raw.get("completion_tokens") or 0,
            reasoning_tokens=completion_details.get("reasoning_tokens") or 0,
            cache_read_tokens=(prompt_details.get("cached_tokens") or raw.get("prompt_cache_hit_tokens") or 0),
        )


def _loads_arguments(raw: Any) -> dict[str, Any]:
    """解析工具参数，模型偶尔会生成非法 JSON，此时退化为空参数"""
    import json

    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
