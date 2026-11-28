"""OpenAI Responses 格式

请求：`POST {base_url}/responses`
消息：`input` 数组，system 提示词由顶层 `instructions` 承载
工具：`tools[].{name,description,parameters}`（扁平结构，无 function 嵌套）
图片：`input` 中的 `input_image` 项，值为 data URI
用量：`input_tokens` / `output_tokens`
"""

from __future__ import annotations

import base64
import binascii
import copy
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..schemas import Completion, ForceTool, ImageContent, Message, ToolCall, Usage
from .base import ImageResponseError, Provider, ProviderError, iter_sse
from .image_options import (
    ANIMATION_FIELDS,
    GeneratedImages,
    ImageCapabilities,
    ImageRequestOptions,
    configured_image_defaults,
    declared_options_error,
)
from .openai_image_limits import supports_official_image_edits, uses_official_image_api

if TYPE_CHECKING:
    from collections.abc import Sequence

    import httpx

    from ..config import ModelConfig
    from ..schemas import ToolChoice, ToolParam


_IMAGE_TOOL_TYPE = "image_generation"
_LEGACY_IMAGE_FIELDS = frozenset(
    {
        "action",
        "background",
        "complexity",
        "input_fidelity",
        "input_image_mask",
        "moderation",
        "output_compression",
        "output_format",
        "partial_images",
        "quality",
        "size",
    }
)
_NATIVE_IMAGE_FIELDS = _LEGACY_IMAGE_FIELDS | {"model"}


def _is_image_tool(tool: object) -> bool:
    return isinstance(tool, dict) and tool.get("type") == _IMAGE_TOOL_TYPE


def _legacy_image_options(body: dict[str, Any]) -> dict[str, Any]:
    # Responses 顶层的 background 是后台执行开关，旧配置用字符串表示图片背景。
    return {
        key: value
        for key, value in body.items()
        if key in _LEGACY_IMAGE_FIELDS and (key != "background" or isinstance(value, str))
    }


def _image_tool_options(model: ModelConfig) -> dict[str, Any]:
    """读取图片工具参数，并兼容优先级更高的旧顶层图片参数。"""
    body = model.extra_body
    options: dict[str, Any] = {}
    tools = body.get("tools", [])
    if isinstance(tools, list):
        for tool in tools:
            if _is_image_tool(tool):
                options.update({key: value for key, value in tool.items() if key in _NATIVE_IMAGE_FIELDS})
    options.update(_legacy_image_options(body))
    return options


def prepare_responses_chat_model(model: ModelConfig) -> ModelConfig:
    """从一次普通对话的配置副本中移除原生绘图设置。"""
    model = model.model_copy(deep=True)
    body = model.extra_body
    for key in _legacy_image_options(body).keys() | ANIMATION_FIELDS:
        body.pop(key, None)

    native_tools = body.get("tools")
    only_image_tools = False
    if isinstance(native_tools, list) and native_tools:
        remaining = [tool for tool in native_tools if not _is_image_tool(tool)]
        body["tools"] = remaining
        only_image_tools = not remaining

    choice = body.get("tool_choice")
    if _is_image_tool(choice) or (choice == "required" and only_image_tools):
        body.pop("tool_choice")
    elif isinstance(choice, dict) and choice.get("type") == "allowed_tools":
        allowed = choice.get("tools")
        if isinstance(allowed, list):
            remaining = [tool for tool in allowed if not _is_image_tool(tool)]
            if remaining:
                choice["tools"] = remaining
            else:
                body.pop("tool_choice")
    return model


@dataclass
class ResponsesCompletion(Completion):
    usage_reported: bool = False


def _has_usage(raw: dict[str, Any] | None) -> bool:
    return bool(raw and raw.keys() & {"input_tokens", "output_tokens"})


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
        tool_choice: ToolChoice = "auto",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "stream": stream,
            "store": False,
            "include": ["reasoning.encrypted_content"],
        }
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
                    # 注册表使用 Python 默认值表示可选参数，不能由 API 自动转为必填。
                    "strict": False,
                }
                for tool in tools
            ]
        extra_body = copy.deepcopy(self.config.extra_body)
        native_tools = extra_body.pop("tools", [])
        if not isinstance(native_tools, list):
            raise ProviderError("Responses extra_body.tools 必须为工具数组")
        payload.update(extra_body)
        if native_tools:
            payload.setdefault("tools", []).extend(native_tools)
        if payload.get("tools") and tool_choice == "none":
            payload["tool_choice"] = "none"
        elif payload.get("tools") and isinstance(tool_choice, ForceTool):
            payload["tool_choice"] = {"type": "function", "name": tool_choice.name}
        return payload

    def image_capabilities(self) -> ImageCapabilities:
        return self._image_capabilities(_image_tool_options(self.config))

    def _image_capabilities(self, parameters: dict[str, Any]) -> ImageCapabilities:
        model_id = parameters.get("model")
        model_id = model_id if isinstance(model_id, str) else ""
        return ImageCapabilities(
            references="vision" in self.config.capabilities,
            continuation=True,
            gif=False,
            explicit_frames=False,
            auto_size=supports_official_image_edits(self.config.base_url, model_id),
            official_geometry=uses_official_image_api(self.config.base_url, model_id),
            defaults=configured_image_defaults(parameters),
        )

    def image_options_error(self, options: ImageRequestOptions) -> str:
        return self._image_options_error(options, _image_tool_options(self.config))

    def _image_options_error(self, options: ImageRequestOptions, parameters: dict[str, Any]) -> str:
        if not isinstance(self.config.extra_body.get("tools", []), list):
            return "extra_body.tools 必须为工具数组"
        effective = options.apply(parameters)
        if effective.get("output_format") == "gif":
            return "此接口不支持动态 GIF"
        if options.frame_count is not None:
            return "--frames 仅适用于 GIF"
        capabilities = self._image_capabilities(parameters)
        return declared_options_error(
            self.config, options, effective, capabilities, native_static=capabilities.auto_size
        )

    async def generate_images(
        self,
        prompt: str,
        *,
        options: ImageRequestOptions,
        images: list[ImageContent] | None = None,
        history: Sequence[Message] = (),
    ) -> GeneratedImages:
        if images and "vision" not in self.config.capabilities:
            raise ProviderError("未声明 vision 能力，不能使用参考图")
        parameters = _image_tool_options(self.config)
        if error := self._image_options_error(options, parameters):
            raise ProviderError(error)
        body = copy.deepcopy(self.config.extra_body)
        native_tools = body.pop("tools", [])
        for key in _legacy_image_options(body).keys() | ANIMATION_FIELDS | {"model", "input", "stream"}:
            body.pop(key, None)
        body["tools"] = [
            *(tool for tool in native_tools if not _is_image_tool(tool)),
            {"type": _IMAGE_TOOL_TYPE, **options.apply(parameters)},
        ]
        body["tool_choice"] = {"type": _IMAGE_TOOL_TYPE}
        model = self.config.model_copy(update={"extra_body": body})
        completion = await ResponsesProvider(model, session_affinity=self.session_affinity).chat(
            [*history, Message.user(prompt, images)]
        )
        usage = completion.usage if isinstance(completion, ResponsesCompletion) and completion.usage_reported else None
        if not completion.images:
            raise ImageResponseError(f"模型 {model.name} 没有生成图片", usage)
        # 只回放产生图片的原生记录，避免重放这次请求中无关的工具输出。
        reusable = [
            item
            for item in completion.message.provider_data.get("responses_output", [])
            if item.get("type") == "image_generation_call" and item.get("id") and item.get("result")
        ]
        continuation = Message.assistant(provider_data={"responses_output": reusable}) if reusable else None
        return GeneratedImages(images=completion.images, usage=usage, continuation=continuation)

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
        self.raise_for_error(data)
        if data.get("status") in ("failed", "cancelled"):
            raise ProviderError("响应生成失败或已取消")
        output_items = data.get("output") or []
        if data.get("status") == "incomplete" and any(item.get("type") == "function_call" for item in output_items):
            raise ProviderError("工具调用尚未完成，请增加 max_tokens 或重试")
        message = self._extract_message(output_items)
        usage = self._parse_usage(data.get("usage"))
        usage_reported = _has_usage(data.get("usage"))
        return ResponsesCompletion(
            message=message,
            usage=usage,
            usage_reported=usage_reported,
            model=data.get("model", ""),
            finish_reason="tool_calls" if message.tool_calls else _finish_reason(data),
            images=_extract_images(output_items, usage if usage_reported else None),
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
        usage_reported = False
        model = ""
        finish_reason = ""
        terminal_response: dict[str, Any] | None = None

        async for event, data in iter_sse(response):
            event = event or data.get("type", "")
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
                    usage_reported = _has_usage(raw_usage)
                if event != "response.created":
                    terminal_response = dict(response_data)
                    terminal_response.setdefault("status", event.removeprefix("response."))
                    terminal_response.setdefault("model", model)
                    # 官方结束事件携带完整快照，以它为准保留加密推理、phase 等原始字段。
                    if isinstance(terminal_response.get("output"), list):
                        return self.parse_response(terminal_response)
                    finish_reason = _finish_reason(terminal_response)
                    break
            elif event == "response.output_text.delta":
                content.append(data.get("delta") or "")
            elif event == "response.refusal.delta":
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

        if terminal_response is None:
            raise ProviderError("流式响应中断，未收到结束事件，请重试")

        # 兼容结束事件省略 output 的服务，优先从已完成的 item 恢复内容。
        for item in raw_output.values():
            if item.get("type") == "function_call":
                item_id = item.get("id") or item.get("call_id") or ""
                if item_id in arguments:
                    item["arguments"] = arguments[item_id]
        output_items = [item for _, item in sorted(raw_output.items())]
        message = self._extract_message(output_items)
        tool_calls = [
            ToolCall(
                id=call_ids.get(item_id, item_id),
                name=names.get(item_id, ""),
                arguments=_loads(arguments.get(item_id)),
            )
            for item_id in order
            if names.get(item_id)
        ]
        if terminal_response.get("status") == "incomplete" and tool_calls:
            raise ProviderError("工具调用尚未完成，请增加 max_tokens 或重试")
        message.content = message.content or "".join(content)
        message.reasoning = message.reasoning or "".join(reasoning)
        message.tool_calls = tool_calls or message.tool_calls
        return ResponsesCompletion(
            message=message,
            usage=usage,
            usage_reported=usage_reported,
            model=model,
            finish_reason="tool_calls" if tool_calls else finish_reason,
            images=_extract_images(output_items, usage if usage_reported else None),
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
                    elif part.get("type") == "refusal":
                        text.append(part.get("refusal") or "")
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


def _extract_images(output_items: list[dict[str, Any]], usage: Usage | None) -> list[ImageContent]:
    """解码原生 image_generation 工具生成的图片"""
    images: list[ImageContent] = []
    for item in output_items:
        if item.get("type") != "image_generation_call" or not (result := item.get("result")):
            continue
        try:
            images.append(ImageContent.from_bytes(base64.b64decode(result, validate=True)))
        except (binascii.Error, TypeError, ValueError) as e:
            raise ImageResponseError("生成图片的数据无效或格式不受支持", usage) from e
    return images


def _loads(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise ProviderError("工具参数包含无效 JSON") from e
    if not isinstance(parsed, dict):
        raise ProviderError("工具参数必须是 JSON 对象")
    return parsed
