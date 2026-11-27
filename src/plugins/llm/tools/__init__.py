"""大模型工具调用。

LLM 内置工具通过 `@registry.register(name, description)` 装饰器注册。普通插件通过
其 PluginMetadata.extra 中的 BusinessTool 声明可选工具，无需加载本插件。
"""

from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING, Any, get_type_hints

from nonebot import get_loaded_plugins
from nonebot.log import logger

from src.utils.llm_tools import BUSINESS_TOOLS_KEY

from ..schemas import ImageContent, ToolParam

if TYPE_CHECKING:
    from collections.abc import Callable, Collection

    from ..config import ModelConfig
    from ..schemas import ToolCall

_TYPE_TO_SCHEMA: dict[Any, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}
"""Python 类型到 JSON Schema 类型的映射"""

_SCHEMA_TO_TYPE: dict[str, Any] = {v: k for k, v in _TYPE_TO_SCHEMA.items()}
"""JSON Schema 类型到 Python 类型的映射"""


@dataclass(frozen=True)
class ToolContext:
    """工具执行时的会话上下文，不暴露给模型。"""

    session_id: str = ""
    """群组会话 ID"""
    image_model: ModelConfig | None = None
    """本群当前使用的生图模型，已回退过全局配置；未开放生图时为空"""


@dataclass
class ToolResult:
    """工具执行结果：交回模型的文本，以及直接发送给用户的图片。"""

    text: str
    """交回模型的文本结果"""
    images: list[ImageContent] = field(default_factory=list)
    """生成后直接发送给用户的图片"""


class ToolRegistry:
    """工具注册表"""

    def __init__(self, *, include_business: bool = False) -> None:
        self._registry: dict[str, dict[str, Any]] = {}
        self._include_business = include_business

    def __len__(self) -> int:
        return len(self._available())

    def register(
        self,
        name: str,
        description: str,
        *,
        needs_context: bool = False,
    ) -> Callable[[Callable], Callable]:
        """注册工具

        参数 schema 由函数签名与 docstring 中的 Args 小节生成，
        无默认值的参数被视为必填。
        """

        def decorator(func: Callable) -> Callable:
            self._registry[name] = _describe_tool(description, func, needs_context=needs_context)
            return func

        return decorator

    def _available(self) -> dict[str, dict[str, Any]]:
        if not self._include_business:
            return self._registry

        # NoneBot 在插件成功加载后才设置 metadata。每次读取时装配，支持任意加载顺序。
        # 同名工具优先使用内置项；业务项之间按插件模块名顺序取第一个。
        available = self._registry.copy()
        loaded = get_loaded_plugins()
        for plugin in sorted(loaded, key=lambda plugin: plugin.module_name):
            if plugin.metadata is None:
                continue
            parent = plugin.parent_plugin
            while parent is not None and parent in loaded:
                parent = parent.parent_plugin
            if parent is not None:
                continue
            for tool in plugin.metadata.extra.get(BUSINESS_TOOLS_KEY, ()):
                if tool.name not in available:
                    available[tool.name] = _describe_tool(tool.description, tool.function)
        return available

    def names(self) -> list[str]:
        """当前可用的全部工具名"""
        return list(self._available())

    def to_params(self, names: Collection[str] | None = None) -> list[ToolParam]:
        """转换为与格式无关的工具定义列表；传入 names 时只保留这些工具"""
        return [
            ToolParam(
                name=name,
                description=info["description"],
                parameters={
                    "type": "object",
                    "properties": info["properties"],
                    "required": info["required"],
                },
            )
            for name, info in self._available().items()
            if names is None or name in names
        ]

    async def execute(self, call: ToolCall, context: ToolContext | None = None) -> str | ToolResult:
        """执行一次工具调用，返回交回模型的结果

        执行失败时返回错误描述而非抛出异常，让模型有机会自行调整。
        """
        info = self._available().get(call.name)
        if not info:
            logger.warning("LLM 请求了未注册的工具")
            return f"错误：未注册的工具 {call.name}"
        started_at = perf_counter()
        argument_names = [name for name in info["properties"] if name in call.arguments]
        logger.info(
            "LLM 工具开始执行（工具={}，参数={}）",
            call.name,
            "、".join(argument_names) or "无",
        )
        try:
            arguments = {
                param_name: _convert_value(call.arguments[param_name], properties["type"])
                for param_name, properties in info["properties"].items()
                if param_name in call.arguments
            }
            missing = [name for name in info["required"] if name not in arguments]
            if missing:
                logger.warning(
                    "LLM 工具缺少必填参数（工具={}，缺少={}，耗时={:.3f}s）",
                    call.name,
                    "、".join(missing),
                    perf_counter() - started_at,
                )
                return f"错误：缺少必填参数 {'、'.join(missing)}"

            if info["needs_context"]:
                if context is None:
                    return f"错误：工具 {call.name} 缺少运行上下文"
                arguments["context"] = context

            result = info["func"](**arguments)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            logger.warning(
                "LLM 工具执行失败（工具={}，错误类型={}，耗时={:.3f}s）",
                call.name,
                type(e).__name__,
                perf_counter() - started_at,
            )
            return f"错误：工具 {call.name} 执行失败：{e}"

        output = (
            result.text
            if isinstance(result, ToolResult)
            else (result if isinstance(result, str) else json.dumps(result, ensure_ascii=False))
        )
        logger.info(
            "LLM 工具执行完成（工具={}，结果字符={}，图片={}，耗时={:.3f}s）",
            call.name,
            len(output),
            len(result.images) if isinstance(result, ToolResult) else 0,
            perf_counter() - started_at,
        )
        return result if isinstance(result, ToolResult) else output


def _describe_tool(description: str, func: Callable, *, needs_context: bool = False) -> dict[str, Any]:
    signature = inspect.signature(func)
    try:
        annotations = get_type_hints(func)
    except (NameError, TypeError):
        annotations = {}
    param_docs = _parse_param_docs(func.__doc__ or "")
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in signature.parameters.items():
        if needs_context and param_name == "context":
            continue
        annotation = annotations.get(param_name, param.annotation)
        properties[param_name] = {
            "type": _TYPE_TO_SCHEMA.get(annotation, "string"),
            "description": param_docs.get(param_name, ""),
        }
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "description": description,
        "func": func,
        "properties": properties,
        "required": required,
        "needs_context": needs_context,
    }


def _parse_param_docs(docstring: str) -> dict[str, str]:
    """从 docstring 的 Args 小节中提取参数说明"""
    param_docs: dict[str, str] = {}
    in_args = False

    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped.lower() in ("args:", "参数:"):
            in_args = True
            continue
        if not in_args:
            continue
        if not stripped:
            continue
        if match := re.match(r"^(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)$", stripped):
            param_docs[match.group(1)] = match.group(2).strip()
        else:
            in_args = False

    return param_docs


def _convert_value(value: Any, schema_type: str) -> Any:
    """把模型传入的参数值转换成 Python 类型

    模型有时会把数字或布尔值写成字符串，这里做一次宽松转换。
    """
    target = _SCHEMA_TO_TYPE.get(schema_type, str)
    if value is None or isinstance(value, target):
        return value
    if target is bool and isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "是")
    return target(value)


registry = ToolRegistry(include_business=True)
"""全局工具注册表"""

# 内置工具在注册表创建后导入，避免模块初始化时的循环依赖。
from . import image as image
from . import web as web
