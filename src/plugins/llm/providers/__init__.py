"""大模型 API 客户端

支持三种对话格式和一种只能生图的格式，通过 `ModelConfig.provider` 选择：

- `openai_chat_completions`：OpenAI Chat Completions，`POST {base_url}/chat/completions`
- `openai_responses`：OpenAI Responses，`POST {base_url}/responses`，也可用原生工具生图
- `anthropic_messages`：Anthropic Messages，`POST {base_url}/v1/messages`
- `openai_images`：OpenAI Image API，支持图片生成、官方参考图编辑，不支持对话
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from .anthropic import AnthropicProvider
from .base import ImageResponseError, Provider, ProviderError, iter_sse
from .chat import ChatProvider
from .image_options import GeneratedImages, ImageCapabilities, ImageRequestOptions
from .images import ImagesClient
from .responses import ResponsesProvider, prepare_responses_chat_model

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..config import ModelConfig
    from ..schemas import ImageContent, Message


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


IMAGE_PROVIDERS: dict[ProviderName, type[ImagesClient | ResponsesProvider]] = {
    ProviderName.OPENAI_IMAGES: ImagesClient,
    ProviderName.OPENAI_RESPONSES: ResponsesProvider,
}
_NO_IMAGE_CAPABILITIES = ImageCapabilities(
    references=False,
    continuation=False,
    gif=False,
    explicit_frames=False,
    auto_size=False,
    official_geometry=False,
    defaults=ImageRequestOptions(),
)


def _image_model_error(model: ModelConfig) -> str:
    if model.provider not in IMAGE_PROVIDERS:
        return f"使用 {model.provider} 接口，暂不支持生图"
    if "image_generation" not in model.capabilities:
        return "未声明 image_generation 能力，不能生成图片"
    if not model.base_url:
        return "未配置 base_url，且未设置 LLM__BASE_URL"
    return ""


def get_image_capabilities(model: ModelConfig) -> ImageCapabilities:
    """查询所选模型的绘图能力和默认参数。"""
    provider = IMAGE_PROVIDERS.get(model.provider)
    if provider is None or "image_generation" not in model.capabilities:
        return _NO_IMAGE_CAPABILITIES
    return provider(model).image_capabilities()


def image_options_error(model: ModelConfig, options: ImageRequestOptions) -> str:
    """检查本轮覆盖与模型默认值合并后的参数，返回可读的错误原因。"""
    if error := _image_model_error(model):
        return error
    return IMAGE_PROVIDERS[model.provider](model).image_options_error(options)


def prepare_chat_model(model: ModelConfig) -> ModelConfig:
    """为普通聊天清理 Responses 的原生绘图设置。"""
    if model.provider == ProviderName.OPENAI_RESPONSES:
        return prepare_responses_chat_model(model)
    return model


async def generate_images(
    model: ModelConfig,
    prompt: str,
    *,
    options: ImageRequestOptions = ImageRequestOptions(),
    session_affinity: str = "",
    images: list[ImageContent] | None = None,
    history: Sequence[Message] = (),
) -> GeneratedImages:
    """使用所选模型的绘图接口完成一次生成或编辑。"""
    if error := _image_model_error(model):
        raise ProviderError(f"生图模型 {model.name} {error}")
    provider = IMAGE_PROVIDERS[model.provider](model, session_affinity=session_affinity)
    return await provider.generate_images(prompt, options=options, images=images, history=history)


__all__ = [
    "LEGACY_PROVIDER_NAMES",
    "PROVIDERS",
    "AnthropicProvider",
    "ChatProvider",
    "GeneratedImages",
    "ImageCapabilities",
    "ImageRequestOptions",
    "ImageResponseError",
    "ImagesClient",
    "Provider",
    "ProviderError",
    "ProviderName",
    "ResponsesProvider",
    "generate_images",
    "get_image_capabilities",
    "get_provider",
    "image_options_error",
    "iter_sse",
    "prepare_chat_model",
]
