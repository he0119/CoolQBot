"""大模型插件配置

环境变量以 `LLM__` 前缀嵌套配置，例如：

```env
LLM__BASE_URL=https://api.example.com
LLM__API_KEY=sk-xxx
LLM__MODELS='[{"name":"model-a","provider":"chat"}]'
```
"""

from typing import Annotated, Any, Literal

from nonebot import get_plugin_config
from pydantic import BaseModel, Field, model_validator

ProviderName = Literal["chat", "responses", "anthropic"]
"""支持的 API 格式"""

ModelCapability = Literal["vision"]
"""可由模型配置显式声明的能力"""

DEFAULT_BASE_URLS: dict[str, str] = {
    "chat": "https://api.deepseek.com",
    "responses": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}
"""各格式的默认服务地址"""

DEEPSEEK_QUOTA_API_URL = "https://api.deepseek.com/user/balance"
"""DeepSeek 官方余额查询地址"""


class BaseQuotaConfig(BaseModel):
    """额度查询的共用配置"""

    api_url: str = ""
    """完整的额度接口地址；留空时回退到全局 LLM 服务地址"""
    api_key: str = ""
    """额度接口密钥；留空时由具体 provider 决定是否复用模型密钥"""
    proxy: str | None = None
    """额度查询代理地址；留空时复用模型代理"""
    timeout: int = 10
    """额度查询超时时间（秒）"""


class ApertureQuotaConfig(BaseQuotaConfig):
    """Tailscale Aperture 额度接口配置"""

    provider: Literal["aperture"]
    bucket: str = ""
    """仅显示指定额度桶；留空时显示接口返回的全部额度桶"""


class DeepSeekQuotaConfig(BaseQuotaConfig):
    """DeepSeek 官方余额接口配置"""

    provider: Literal["deepseek"]


QuotaConfig = Annotated[ApertureQuotaConfig | DeepSeekQuotaConfig, Field(discriminator="provider")]
"""单个模型的额度查询配置"""


class ModelConfig(BaseModel):
    """单个模型的配置"""

    name: str
    """模型标识，命令中使用此名称选择模型"""
    model: str = ""
    """传给 API 的模型名，留空时与 name 相同"""
    provider: ProviderName = "chat"
    """API 格式"""
    base_url: str = ""
    """服务地址，留空时回退到全局 base_url 或按格式取默认值"""
    api_key: str = ""
    """密钥，留空时回退到全局 api_key"""
    prompt: str = ""
    """人设，留空时回退到全局 prompt"""
    proxy: str | None = None
    """代理地址"""
    stream: bool | None = None
    """是否流式请求，留空时回退到全局 stream"""
    max_tokens: int | None = None
    """最大输出 token 数"""
    temperature: float | None = None
    """采样温度"""
    timeout: int = 120
    """非流式请求的超时时间（秒）"""
    extra_body: dict[str, Any] = Field(default_factory=dict)
    """附加到请求体的额外字段，用于传递各服务商的特有参数"""
    capabilities: set[ModelCapability] = Field(default_factory=set)
    """模型能力；vision 表示可直接接收图片"""
    quota: QuotaConfig | None = None
    """该模型的额度查询配置，留空时不支持额度查询"""

    @model_validator(mode="after")
    def fill_defaults(self) -> "ModelConfig":
        if not self.model:
            self.model = self.name
        return self


class ScopedConfig(BaseModel):
    """大模型插件配置"""

    base_url: str = ""
    """全局服务地址，未单独配置服务地址的模型都使用它"""
    api_key: str = ""
    """全局密钥，未单独配置密钥的模型都使用它"""
    models: list[ModelConfig] = Field(default_factory=list)
    """可用模型列表，第一个为默认模型"""
    prompt: str = ""
    """全局人设"""
    stream: bool = False
    """是否流式请求"""
    send_thinking: bool = False
    """是否附带推理内容"""
    md_to_pic: bool = False
    """是否把回复渲染成图片"""
    context_timeout: int = 120
    """多轮对话中等待用户输入的超时时间（秒）"""
    max_tool_rounds: int = 5
    """单次提问中允许的最大工具调用轮数，防止模型陷入循环"""
    zssm_model: str = ""
    """解释模式使用的模型；留空时使用当前群组模型"""
    zssm_vision_model: str = ""
    """解释模型不支持图片时使用的视觉模型；必须声明 vision 能力"""
    zssm_max_images: int = 2
    """解释模式单次允许的最大图片数量"""
    zssm_max_image_bytes: int = 10 * 1024 * 1024
    """解释模式单张图片的最大字节数"""
    zssm_max_resources: int = 2
    """解释模式单次读取的最大网页或 PDF 数量"""
    zssm_max_resource_bytes: int = 10 * 1024 * 1024
    """解释模式单个网页或 PDF 的最大下载字节数"""
    zssm_max_resource_chars: int = 30_000
    """解释模式单个网页或 PDF 提取后的最大字符数"""
    zssm_max_pdf_pages: int = 50
    """解释模式读取 PDF 的最大页数"""
    zssm_resource_timeout: int = 30
    """解释模式下载网页或 PDF 的超时时间（秒）"""
    zssm_resource_proxy: str | None = None
    """解释模式下载网页或 PDF 使用的代理"""
    tts_base_url: str = ""
    """GPT-SoVITS 服务地址，留空则禁用语音功能"""
    tts_access_token: str = ""
    """GPT-SoVITS 访问令牌"""
    tts_model: str = ""
    """默认 TTS 模型名"""
    tts_timeout: int = 60
    """TTS 请求超时时间（秒）"""

    def get_model_names(self) -> list[str]:
        """获取所有可用模型名"""
        return [model.name for model in self.models]

    def get_model(self, name: str) -> ModelConfig:
        """按名称获取模型配置"""
        for model in self.models:
            if model.name == name:
                return model
        raise ValueError(f"未启用的模型：{name}")

    def resolve(self, name: str) -> ModelConfig:
        """获取模型配置，并把留空字段回退到全局配置

        返回副本，避免污染原始配置。
        """
        model = self.get_model(name).model_copy()
        if not model.base_url:
            model.base_url = self.base_url or DEFAULT_BASE_URLS[model.provider]
        if not model.api_key:
            model.api_key = self.api_key
        if not model.prompt:
            model.prompt = self.prompt
        if model.stream is None:
            model.stream = self.stream
        return model

    @property
    def tts_enabled(self) -> bool:
        """TTS 功能是否可用"""
        return bool(self.tts_base_url)


class Config(BaseModel):
    """插件配置入口"""

    llm: ScopedConfig = Field(default_factory=ScopedConfig)
    """大模型插件配置"""


plugin_config = get_plugin_config(Config).llm
