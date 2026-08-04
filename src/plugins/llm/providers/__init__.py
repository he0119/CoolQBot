"""大模型 API 客户端

支持三种请求格式，通过 `ModelConfig.provider` 选择：

- `openai_chat_completions`：OpenAI Chat Completions，`POST {base_url}/chat/completions`
- `openai_responses`：OpenAI Responses，`POST {base_url}/responses`
- `anthropic_messages`：Anthropic Messages，`POST {base_url}/v1/messages`
"""

from enum import StrEnum

from .anthropic import AnthropicProvider
from .base import Provider, ProviderError, iter_sse
from .chat import ChatProvider
from .responses import ResponsesProvider


class ProviderName(StrEnum):
    """支持的大模型 API 协议。"""

    OPENAI_CHAT_COMPLETIONS = "openai_chat_completions"
    OPENAI_RESPONSES = "openai_responses"
    ANTHROPIC_MESSAGES = "anthropic_messages"


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
"""API 协议到实现的映射。"""


def get_provider(name: ProviderName | str) -> type[Provider]:
    """根据协议名获取对应的 Provider 实现。"""
    try:
        provider_name = LEGACY_PROVIDER_NAMES[name] if name in LEGACY_PROVIDER_NAMES else ProviderName(name)
    except ValueError as e:
        choices = "、".join(item.value for item in ProviderName)
        raise ProviderError(f"不支持的 API 格式：{name}，可选：{choices}") from e
    return PROVIDERS[provider_name]


__all__ = [
    "LEGACY_PROVIDER_NAMES",
    "PROVIDERS",
    "AnthropicProvider",
    "ChatProvider",
    "Provider",
    "ProviderError",
    "ProviderName",
    "ResponsesProvider",
    "get_provider",
    "iter_sse",
]
