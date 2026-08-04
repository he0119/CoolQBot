"""大模型插件配置

环境变量以 `LLM__` 前缀嵌套配置，例如：

```env
LLM__BASE_URL=https://api.example.com
LLM__API_KEY=sk-xxx
LLM__MODELS='[{"name":"model-a","provider":"openai_chat_completions"}]'
```
"""

from enum import StrEnum
from typing import Annotated, Any, Literal

from nonebot import get_plugin_config, logger
from pydantic import AliasChoices, BaseModel, Field, model_validator

from .providers import LEGACY_PROVIDER_NAMES, ProviderName


class ModelCapability(StrEnum):
    """模型可声明的输入能力。"""

    TEXT = "text"
    VISION = "vision"


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
    provider: ProviderName = ProviderName.OPENAI_CHAT_COMPLETIONS
    """API 格式"""
    base_url: str = ""
    """服务地址，留空时回退到全局 base_url"""
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
    capabilities: set[ModelCapability] = Field(default_factory=lambda: {ModelCapability.TEXT})
    """模型能力；默认支持文本，vision 表示可直接接收图片"""
    quota: QuotaConfig | None = None
    """该模型的额度查询配置，留空时不支持额度查询"""

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_provider(cls, data: Any) -> Any:
        """临时兼容旧 Provider 名称，并提示迁移。"""
        if not isinstance(data, dict):
            return data
        legacy_name = data.get("provider")
        if not isinstance(legacy_name, str) or legacy_name not in LEGACY_PROVIDER_NAMES:
            return data

        provider = LEGACY_PROVIDER_NAMES[legacy_name]
        logger.warning(
            "模型 Provider 配置已弃用（模型={}，旧值={}，新值={}，将在下个版本移除）",
            data.get("name", "未命名"),
            legacy_name,
            provider.value,
        )
        return {**data, "provider": provider}

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
    prefer_markdown: bool = False
    """是否在 QQ 平台优先使用原生 Markdown 回复"""
    md_to_pic: bool = False
    """是否把回复渲染成图片"""
    respond_to_mention: bool = True
    """是否响应被适配器判定为发给机器人的消息（如群聊 @）"""
    context_timeout: int = 120
    """多轮对话中等待用户输入的超时时间（秒）"""
    max_tool_rounds: int = 10
    """单次提问中允许的最大工具调用轮数，达到上限后禁用工具生成收尾回复"""
    tool_notice_delay: float = Field(default=10.0, ge=0)
    """发现工具调用后首次发送等待提示前的秒数"""
    tool_notice_interval: float = Field(default=60.0, gt=0)
    """工具阶段仍未完成时重复发送等待提示的间隔秒数"""
    web_search_max_results: int = Field(default=5, ge=1, le=10)
    """网页搜索单次允许返回的最大结果数"""
    web_search_timeout: int = Field(default=10, gt=0)
    """网页搜索超时时间（秒）"""
    web_search_region: str = "wt-wt"
    """网页搜索区域代码，wt-wt 表示不限定区域"""
    web_search_safesearch: Literal["on", "moderate", "off"] = "moderate"
    """网页搜索安全过滤级别"""
    web_search_backend: str = "auto"
    """网页搜索后端，默认由 ddgs 自动选择"""
    web_fetch_max_bytes: int = Field(
        default=10 * 1024 * 1024,
        gt=0,
        validation_alias=AliasChoices("web_fetch_max_bytes", "zssm_max_resource_bytes"),
    )
    """web_fetch 与解释模式单个网页或 PDF 的最大下载字节数"""
    web_fetch_max_chars: int = Field(
        default=30_000,
        gt=0,
        validation_alias=AliasChoices("web_fetch_max_chars", "zssm_max_resource_chars"),
    )
    """web_fetch 与解释模式单个网页或 PDF 提取后的最大字符数"""
    web_fetch_max_pdf_pages: int = Field(
        default=50,
        gt=0,
        validation_alias=AliasChoices("web_fetch_max_pdf_pages", "zssm_max_pdf_pages"),
    )
    """web_fetch 与解释模式读取 PDF 的最大页数"""
    web_fetch_timeout: int = Field(
        default=30,
        gt=0,
        validation_alias=AliasChoices("web_fetch_timeout", "zssm_resource_timeout"),
    )
    """web_fetch 与解释模式下载网页或 PDF 的超时时间（秒）"""
    web_proxy: str | None = Field(
        default=None,
        validation_alias=AliasChoices("web_proxy", "zssm_resource_proxy"),
    )
    """网页搜索、web_fetch 与解释模式下载网页或 PDF 使用的代理"""
    web_fetch_fake_ip_ranges: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("web_fetch_fake_ip_ranges", "zssm_resource_fake_ip_ranges"),
    )
    """web_fetch 与解释模式允许的代理 fake-ip 网段；不放宽 URL 中直接填写的 IP"""
    zssm_max_images: int = 2
    """解释模式单次允许的最大图片数量"""
    zssm_max_image_bytes: int = 10 * 1024 * 1024
    """解释模式单张图片的最大字节数"""
    zssm_max_resources: int = 2
    """解释模式单次读取的最大网页或 PDF 数量"""
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
            model.base_url = self.base_url
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
