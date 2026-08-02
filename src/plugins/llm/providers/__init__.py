"""大模型 API 客户端

支持三种请求格式，通过 `ModelConfig.provider` 选择：

- `chat`：OpenAI Chat Completions，`POST {base_url}/chat/completions`
- `responses`：OpenAI Responses，`POST {base_url}/responses`
- `anthropic`：Anthropic Messages，`POST {base_url}/v1/messages`
"""

from .anthropic import AnthropicProvider
from .base import Provider, ProviderError, iter_sse
from .chat import ChatProvider
from .responses import ResponsesProvider

PROVIDERS: dict[str, type[Provider]] = {
    "chat": ChatProvider,
    "responses": ResponsesProvider,
    "anthropic": AnthropicProvider,
}
"""格式名到实现的映射"""


def get_provider(name: str) -> type[Provider]:
    """根据格式名获取对应的 provider 实现"""
    if name not in PROVIDERS:
        raise ProviderError(f"不支持的 API 格式：{name}，可选：{'、'.join(PROVIDERS)}")
    return PROVIDERS[name]


__all__ = [
    "PROVIDERS",
    "AnthropicProvider",
    "ChatProvider",
    "Provider",
    "ProviderError",
    "ResponsesProvider",
    "get_provider",
    "iter_sse",
]
