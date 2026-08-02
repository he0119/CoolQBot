"""大模型插件配置

环境变量以 `LLM__` 前缀嵌套配置，例如：

```env
LLM__API_KEY=sk-xxx
LLM__MODELS='[{"name":"claude","provider":"anthropic","model":"claude-opus-5","base_url":"https://api.anthropic.com","api_key":"sk-ant-xxx"}]'
```
"""

from typing import Any, Literal

from nonebot import get_plugin_config
from pydantic import BaseModel, Field, model_validator

ProviderName = Literal["chat", "responses", "anthropic"]
"""支持的 API 格式"""

DEFAULT_BASE_URLS: dict[str, str] = {
    "chat": "https://api.deepseek.com",
    "responses": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}
"""各格式的默认服务地址"""


class ModelConfig(BaseModel):
    """单个模型的配置"""

    name: str
    """模型标识，命令中使用此名称选择模型"""
    model: str = ""
    """传给 API 的模型名，留空时与 name 相同"""
    provider: ProviderName = "chat"
    """API 格式"""
    base_url: str = ""
    """服务地址，留空时按格式取默认值"""
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

    @model_validator(mode="after")
    def fill_defaults(self) -> "ModelConfig":
        if not self.model:
            self.model = self.name
        if not self.base_url:
            self.base_url = DEFAULT_BASE_URLS[self.provider]
        return self


class ScopedConfig(BaseModel):
    """大模型插件配置"""

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
