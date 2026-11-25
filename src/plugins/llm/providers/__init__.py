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

from ..schemas import Message
from .anthropic import AnthropicProvider
from .base import Provider, ProviderError, iter_sse
from .chat import ChatProvider
from .images import GeneratedImages, ImagesClient
from .responses import ResponsesProvider

if TYPE_CHECKING:
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


async def generate_images(model: ModelConfig, prompt: str, *, session_affinity: str = "") -> GeneratedImages:
    """用生图模型按提示词生成图片

    - `openai_images`：调用 Image API
    - `openai_responses`：强制调用 Responses 原生 image_generation 工具，适合既能对话又能生图的模型
    """
    if model.provider == ProviderName.OPENAI_IMAGES:
        return await ImagesClient(model, session_affinity=session_affinity).generate(prompt)
    if model.provider != ProviderName.OPENAI_RESPONSES:
        raise ProviderError(f"模型 {model.name} 使用 {model.provider} 接口，暂不支持生图")

    model = model.model_copy(deep=True)
    native_tools: Any = model.extra_body.get("tools") or []
    if not isinstance(native_tools, list):
        raise ProviderError(f"模型 {model.name} 的 extra_body.tools 必须为工具数组")
    model.extra_body["tools"] = [*native_tools, {"type": "image_generation"}]
    model.extra_body["tool_choice"] = {"type": "image_generation"}
    completion = await ResponsesProvider(model, session_affinity=session_affinity).chat([Message.user(prompt)])
    if not completion.images:
        raise ProviderError(f"模型 {model.name} 没有生成图片")
    return GeneratedImages(images=completion.images, usage=completion.usage)


__all__ = [
    "LEGACY_PROVIDER_NAMES",
    "PROVIDERS",
    "AnthropicProvider",
    "ChatProvider",
    "GeneratedImages",
    "ImagesClient",
    "Provider",
    "ProviderError",
    "ProviderName",
    "ResponsesProvider",
    "generate_images",
    "get_provider",
    "iter_sse",
]
