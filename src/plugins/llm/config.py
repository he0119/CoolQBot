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
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ModelWrapValidatorHandler,
    ValidationError,
    field_validator,
    model_validator,
)

from .providers import LEGACY_PROVIDER_NAMES, ProviderName
from .quota import QuotaConfig


class ModelCapability(StrEnum):
    """模型可声明的能力。"""

    TEXT = "text"
    """能处理文本对话"""
    VISION = "vision"
    """能直接接收图片输入"""
    IMAGE_GENERATION = "image_generation"
    """能生成图片，可被设为本群生图模型"""


IMAGE_GENERATION_PROVIDERS = frozenset({ProviderName.OPENAI_IMAGES, ProviderName.OPENAI_RESPONSES})
"""能生成图片的接口：openai_images 调用 Image API，openai_responses 使用原生 image_generation 工具"""


ImageFormat = Literal["gif", "png", "jpeg", "webp"]
ImageSize = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,4}x[1-9][0-9]{0,4}$")]


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
    """模型能力；是否能对话、看图、生图都只看这里的声明

    默认为 text；openai_images 接口只能生图，省略时默认为 image_generation。
    """
    image_output_formats: set[ImageFormat] = Field(default_factory=set)
    """该模型的网关接受的可变输出格式；gif 声明必须代表支持多帧。"""
    image_sizes: set[ImageSize] = Field(default_factory=set)
    """该模型的网关接受的可变像素尺寸，例：2048x2048。"""
    image_sizes_by_format: dict[ImageFormat, set[ImageSize]] = Field(default_factory=dict)
    """按格式覆盖 image_sizes，例如为 GIF 单独声明已验证的帧尺寸。"""
    quota: QuotaConfig | None = None
    """该模型的额度查询配置，留空时不支持额度查询"""

    @model_validator(mode="after")
    def fill_defaults(self) -> "ModelConfig":
        if not self.model:
            self.model = self.name
        if self.provider == ProviderName.OPENAI_IMAGES and "capabilities" not in self.model_fields_set:
            self.capabilities = {ModelCapability.IMAGE_GENERATION}
        return self

    @model_validator(mode="after")
    def check_capabilities(self) -> "ModelConfig":
        """能力声明必须是接口真正做得到的，避免运行时才发现不能对话或不能生图。"""
        if self.provider == ProviderName.OPENAI_IMAGES:
            if self.capabilities != {ModelCapability.IMAGE_GENERATION}:
                raise ValueError(
                    f"模型 {self.name} 使用 openai_images 接口，只能生图，capabilities 只能是 image_generation；"
                    "既能对话又能生图的模型请改用 openai_responses 接口"
                )
        elif ModelCapability.IMAGE_GENERATION in self.capabilities and self.provider not in IMAGE_GENERATION_PROVIDERS:
            raise ValueError(
                f"模型 {self.name} 使用 {self.provider} 接口，暂不支持生图；"
                "生图模型请使用 openai_images 或 openai_responses 接口"
            )
        if ("gif" in self.image_output_formats or "gif" in self.image_sizes_by_format) and (
            self.provider != ProviderName.OPENAI_IMAGES
        ):
            raise ValueError(f"模型 {self.name} 的接口不支持动态 GIF 扩展")
        return self

    @model_validator(mode="wrap")
    @classmethod
    def migrate_legacy_provider(cls, data: Any, handler: ModelWrapValidatorHandler["ModelConfig"]) -> "ModelConfig":
        """临时兼容旧 Provider 名称，仅对通过校验的模型提示迁移。"""
        legacy_name = data.get("provider") if isinstance(data, dict) else None
        if not isinstance(legacy_name, str) or legacy_name not in LEGACY_PROVIDER_NAMES:
            return handler(data)

        provider = LEGACY_PROVIDER_NAMES[legacy_name]
        model = handler({**data, "provider": provider})
        logger.warning(
            "模型 Provider 配置已弃用（模型={}，旧值={}，新值={}，将在下个版本移除）",
            model.name,
            legacy_name,
            provider.value,
        )
        return model


class ScopedConfig(BaseModel):
    """大模型插件配置"""

    model_config = ConfigDict(hide_input_in_errors=True)

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
    max_requests: int = Field(default=10, ge=2)
    """单次提问允许的最大模型请求次数，最后一次请求禁止工具调用并生成收尾回复"""
    request_notice_delay: float = Field(default=20.0, ge=0)
    """Agent 首次模型请求开始后发送等待提示前的秒数"""
    request_notice_interval: float = Field(default=60.0, gt=0)
    """Agent 请求仍未完成时重复发送等待提示的间隔秒数"""
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

    @field_validator("models", mode="before")
    @classmethod
    def validate_model_entries(cls, value: Any) -> Any:
        if not isinstance(value, list) or not value:
            return value

        valid: list[ModelConfig] = []
        invalid: list[str] = []
        for index, entry in enumerate(value):
            try:
                valid.append(ModelConfig.model_validate(entry))
            except ValidationError as exc:
                issues = []
                for error in exc.errors(include_input=False, include_context=False, include_url=False):
                    location = error["loc"]
                    # 深层位置可能包含输入字典的键；只输出已声明的顶层字段和错误码。
                    field = f"{location[0]}:" if location and location[0] in ModelConfig.model_fields else ""
                    issues.append(f"{field}{error['type']}")
                invalid.append(f"models[{index}] ({', '.join(dict.fromkeys(issues))})")

        if not valid:
            raise ValueError(f"没有通过校验的 LLM 模型配置：{'; '.join(invalid)}")
        for rejection in invalid:
            logger.warning("忽略无效模型配置 {}", rejection)
        return valid

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

    model_config = ConfigDict(hide_input_in_errors=True)

    llm: ScopedConfig = Field(default_factory=ScopedConfig)
    """大模型插件配置"""


plugin_config = get_plugin_config(Config).llm
