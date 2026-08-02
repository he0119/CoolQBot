"""统一的大模型数据结构

三种 API 格式（OpenAI Chat Completions / OpenAI Responses / Anthropic Messages）
的请求与响应在这里被归一化为同一套内部结构，供 handler 与命令层使用。
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ImageContent:
    """图片内容"""

    data: bytes
    """图片二进制数据"""
    mimetype: str = "image/png"
    """图片类型"""

    @classmethod
    def from_bytes(cls, data: bytes) -> ImageContent:
        """根据文件签名构造图片内容"""
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            mimetype = "image/png"
        elif data.startswith(b"\xff\xd8\xff"):
            mimetype = "image/jpeg"
        elif data.startswith((b"GIF87a", b"GIF89a")):
            mimetype = "image/gif"
        elif len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            mimetype = "image/webp"
        else:
            raise ValueError("不支持的图片格式，仅支持 PNG、JPEG、GIF 和 WebP")
        return cls(data=data, mimetype=mimetype)

    def to_base64(self) -> str:
        """转换为 base64 字符串（不含 data URI 前缀）"""
        return base64.b64encode(self.data).decode()

    def to_data_uri(self) -> str:
        """转换为 data URI"""
        return f"data:{self.mimetype};base64,{self.to_base64()}"


@dataclass
class ToolCall:
    """模型请求的工具调用"""

    id: str
    """工具调用 ID，回传结果时需要原样带上"""
    name: str
    """工具名称"""
    arguments: dict[str, Any]
    """工具参数"""

    def arguments_json(self) -> str:
        """参数的 JSON 字符串形式"""
        return json.dumps(self.arguments, ensure_ascii=False)


@dataclass
class Message:
    """一条对话消息"""

    role: Role
    """角色"""
    content: str = ""
    """文本内容"""
    images: list[ImageContent] = field(default_factory=list)
    """图片内容，仅 user 消息有效"""
    reasoning: str = ""
    """推理内容，仅 assistant 消息有效"""
    tool_calls: list[ToolCall] = field(default_factory=list)
    """模型请求的工具调用，仅 assistant 消息有效"""
    tool_call_id: str = ""
    """所回复的工具调用 ID，仅 tool 消息有效"""
    provider_data: dict[str, Any] = field(default_factory=dict)
    """供应商协议的原始数据，仅用于后续请求无损回放"""

    @classmethod
    def user(cls, content: str, images: list[ImageContent] | None = None) -> Message:
        """构造用户消息"""
        return cls(role="user", content=content, images=images or [])

    @classmethod
    def assistant(
        cls,
        content: str = "",
        reasoning: str = "",
        tool_calls: list[ToolCall] | None = None,
        provider_data: dict[str, Any] | None = None,
    ) -> Message:
        """构造助手消息"""
        return cls(
            role="assistant",
            content=content,
            reasoning=reasoning,
            tool_calls=tool_calls or [],
            provider_data=provider_data or {},
        )

    @classmethod
    def tool(cls, tool_call_id: str, content: str) -> Message:
        """构造工具结果消息"""
        return cls(role="tool", content=content, tool_call_id=tool_call_id)


@dataclass
class Usage:
    """token 用量

    三种格式的字段名各不相同，统一归一化到这里：

    - Chat Completions: `prompt_tokens` / `completion_tokens`
    - Responses: `input_tokens` / `output_tokens`
    - Anthropic: `input_tokens` / `output_tokens` + 缓存相关字段
    """

    input_tokens: int = 0
    """输入 token 数（不含缓存命中部分时由各 provider 自行说明）"""
    output_tokens: int = 0
    """输出 token 数"""
    reasoning_tokens: int = 0
    """推理 token 数，属于 output_tokens 的一部分"""
    cache_read_tokens: int = 0
    """缓存命中的 token 数"""
    cache_write_tokens: int = 0
    """写入缓存的 token 数，仅 Anthropic 提供"""

    @property
    def total_tokens(self) -> int:
        """总 token 数"""
        return self.input_tokens + self.output_tokens

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
        )

    def to_chinese(self) -> str:
        """转换为中文描述"""
        parts = [f"输入 {self.input_tokens}", f"输出 {self.output_tokens}"]
        if self.reasoning_tokens:
            parts.append(f"推理 {self.reasoning_tokens}")
        if self.cache_read_tokens:
            parts.append(f"缓存命中 {self.cache_read_tokens}")
        if self.cache_write_tokens:
            parts.append(f"缓存写入 {self.cache_write_tokens}")
        return "，".join(parts)


@dataclass
class Completion:
    """一次模型调用的结果"""

    message: Message
    """模型返回的消息"""
    usage: Usage = field(default_factory=Usage)
    """本次调用的用量"""
    model: str = ""
    """实际使用的模型名"""
    finish_reason: str = ""
    """结束原因，已归一化为 stop / length / tool_calls / content_filter"""
    elapsed_seconds: float = 0.0
    """完成本次提问的耗时（秒）"""

    @property
    def content(self) -> str:
        """模型返回的文本内容"""
        return self.message.content

    @property
    def reasoning(self) -> str:
        """模型返回的推理内容"""
        return self.message.reasoning

    @property
    def tool_calls(self) -> list[ToolCall]:
        """模型请求的工具调用"""
        return self.message.tool_calls


@dataclass
class ToolParam:
    """工具定义

    保存与格式无关的描述，由各 provider 转换成自己的 schema。
    """

    name: str
    """工具名称"""
    description: str
    """工具说明，模型据此判断何时调用"""
    parameters: dict[str, Any]
    """JSON Schema 格式的参数定义"""
