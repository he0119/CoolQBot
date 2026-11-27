"""大模型 API 客户端

支持三种对话格式和一种只能生图的格式，通过 `ModelConfig.provider` 选择：

- `openai_chat_completions`：OpenAI Chat Completions，`POST {base_url}/chat/completions`
- `openai_responses`：OpenAI Responses，`POST {base_url}/responses`，也可用原生工具生图
- `anthropic_messages`：Anthropic Messages，`POST {base_url}/v1/messages`
- `openai_images`：OpenAI Image API，`POST {base_url}/images/generations`，只能生图，不能对话
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from ..schemas import ImageContent, Message
from .anthropic import AnthropicProvider
from .base import ImageResponseError, Provider, ProviderError, iter_sse
from .chat import ChatProvider
from .images import GeneratedImages, ImagesClient
from .responses import ResponsesCompletion, ResponsesProvider

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..config import ModelConfig


class ProviderName(StrEnum):
    """支持的大模型 API 协议。"""

    OPENAI_CHAT_COMPLETIONS = "openai_chat_completions"
    OPENAI_RESPONSES = "openai_responses"
    ANTHROPIC_MESSAGES = "anthropic_messages"
    OPENAI_IMAGES = "openai_images"


LEGACY_PROVIDER_NAMES: dict[str, ProviderName] = {
    "chat": ProviderName.OPENAI_CHAT_COMPLETIONS,
    "responses": ProviderName.OPENAI_RESPONSES,
    "anthropic": ProviderName.ANTHROPIC_MESSAGES,
}
"""当前版本临时兼容的旧 Provider 名称。"""


PROVIDERS: dict[ProviderName, type[Provider]] = {
    ProviderName.OPENAI_CHAT_COMPLETIONS: ChatProvider,
    ProviderName.OPENAI_RESPONSES: ResponsesProvider,
    ProviderName.ANTHROPIC_MESSAGES: AnthropicProvider,
}
"""对话协议到实现的映射；openai_images 只能生图，不在这里。"""


def get_provider(name: ProviderName | str) -> type[Provider]:
    """根据协议名获取对应的对话 Provider 实现。"""
    try:
        provider_name = LEGACY_PROVIDER_NAMES[name] if name in LEGACY_PROVIDER_NAMES else ProviderName(name)
    except ValueError as e:
        choices = "、".join(item.value for item in ProviderName)
        raise ProviderError(f"不支持的 API 格式：{name}，可选：{choices}") from e
    if provider_name not in PROVIDERS:
        raise ProviderError(f"{provider_name} 接口只能生图，不能对话")
    return PROVIDERS[provider_name]


IMAGE_TOOL_KEYS = frozenset(
    {"size", "quality", "background", "output_format", "output_compression", "moderation", "action"}
)
ANIMATION_KEYS = frozenset({"frames", "frame_count", "frame_duration", "frame_duration_ms", "duration"})


def image_tool_options(model: ModelConfig) -> dict[str, Any]:
    """解析固定图片参数；顶层设置优先于旧 Responses 工具中的同名设置。"""
    options: dict[str, Any] = {}
    native_tools = model.extra_body.get("tools", [])
    if model.provider == ProviderName.OPENAI_RESPONSES and isinstance(native_tools, list):
        for tool in native_tools:
            if isinstance(tool, dict) and tool.get("type") == "image_generation":
                options.update({key: tool[key] for key in IMAGE_TOOL_KEYS if key in tool})
    options.update({key: model.extra_body[key] for key in IMAGE_TOOL_KEYS if key in model.extra_body})
    return options


async def generate_images(
    model: ModelConfig,
    prompt: str,
    *,
    session_affinity: str = "",
    images: list[ImageContent] | None = None,
    history: Sequence[Message] = (),
) -> GeneratedImages:
    """只通过选中模型自身的接入执行一次图片请求。"""
    if not model.base_url:
        raise ProviderError(f"生图模型 {model.name} 未配置 base_url，且未设置 LLM__BASE_URL")
    if model.provider == ProviderName.OPENAI_IMAGES:
        if images or history:
            raise ProviderError("此生图模型只能生成图片，不能使用参考图或续画")
        if model.extra_body.get("output_format") != "gif":
            model = model.model_copy(
                update={
                    "extra_body": {key: value for key, value in model.extra_body.items() if key not in ANIMATION_KEYS}
                }
            )
        return await ImagesClient(model, session_affinity=session_affinity).generate(prompt)
    if model.provider != ProviderName.OPENAI_RESPONSES:
        raise ProviderError(f"模型 {model.name} 使用 {model.provider} 接口，暂不支持生图")

    model = model.model_copy(deep=True)
    body = model.extra_body
    native_tools: Any = body.get("tools", [])
    if not isinstance(native_tools, list):
        raise ProviderError(f"模型 {model.name} 的 extra_body.tools 必须为工具数组")
    options = image_tool_options(model)
    if options.get("output_format") == "gif":
        raise ProviderError(f"生图模型 {model.name} 的 Responses 接口不支持动态 GIF")
    image_tool = {"type": "image_generation", **options}
    for key in IMAGE_TOOL_KEYS | ANIMATION_KEYS | {"model", "input", "stream"}:
        body.pop(key, None)
    body["tools"] = [
        *(tool for tool in native_tools if not isinstance(tool, dict) or tool.get("type") != "image_generation"),
        image_tool,
    ]
    body["tool_choice"] = {"type": "image_generation"}
    completion = await ResponsesProvider(model, session_affinity=session_affinity).chat(
        [*history, Message.user(prompt, images)]
    )
    usage = completion.usage if isinstance(completion, ResponsesCompletion) and completion.usage_reported else None
    if not completion.images:
        raise ImageResponseError(f"模型 {model.name} 没有生成图片", usage)
    # 只保留原生图片输出；不重放 Responses 的无关工具或把图片变成通用 assistant 图片。
    items = completion.message.provider_data.get("responses_output", [])
    reusable = [
        item for item in items if item.get("type") == "image_generation_call" and item.get("id") and item.get("result")
    ]
    continuation = Message.assistant(provider_data={"responses_output": reusable}) if reusable else None
    return GeneratedImages(images=completion.images, usage=usage, continuation=continuation)


__all__ = [
    "LEGACY_PROVIDER_NAMES",
    "PROVIDERS",
    "AnthropicProvider",
    "ChatProvider",
    "GeneratedImages",
    "ImageResponseError",
    "ImagesClient",
    "Provider",
    "ProviderError",
    "ProviderName",
    "ResponsesProvider",
    "generate_images",
    "get_provider",
    "iter_sse",
]
