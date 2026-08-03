"""大模型工具调用

通过 `@registry.register(name, description)` 装饰器注册工具，运行时根据模型
请求的参数自动转换并执行，执行结果作为下一轮对话的上下文交回模型。

业务插件按需向注册表登记工具。当前内置天气与节假日查询，也可以继续在自己的模块中注册：

```python
from src.plugins.llm.tools import registry

@registry.register("get_weather", "查询指定城市的天气")
async def get_weather(city: str) -> str:
    \"\"\"查询天气

    Args:
        city: 城市名称
    \"\"\"
    return "晴，25 度"
```
"""

from __future__ import annotations

import inspect
import json
import re
from time import perf_counter
from typing import TYPE_CHECKING, Any, get_type_hints

from nonebot.log import logger

from ..schemas import ToolParam

if TYPE_CHECKING:
    from collections.abc import Callable, Collection

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


class ToolRegistry:
    """工具注册表"""

    def __init__(self) -> None:
        self._registry: dict[str, dict[str, Any]] = {}

    def __len__(self) -> int:
        return len(self._registry)

    def register(
        self,
        name: str,
        description: str,
        *,
        group: str | None = None,
    ) -> Callable[[Callable], Callable]:
        """注册工具

        参数 schema 由函数签名与 docstring 中的 Args 小节生成，
        无默认值的参数被视为必填。设置 group 后，工具只在显式启用该分组时可用。
        """

        def decorator(func: Callable) -> Callable:
            signature = inspect.signature(func)
            try:
                annotations = get_type_hints(func)
            except (NameError, TypeError):
                annotations = {}
            param_docs = _parse_param_docs(func.__doc__ or "")
            properties: dict[str, Any] = {}
            required: list[str] = []

            for param_name, param in signature.parameters.items():
                annotation = annotations.get(param_name, param.annotation)
                properties[param_name] = {
                    "type": _TYPE_TO_SCHEMA.get(annotation, "string"),
                    "description": param_docs.get(param_name, ""),
                }
                if param.default is inspect.Parameter.empty:
                    required.append(param_name)

            self._registry[name] = {
                "description": description,
                "func": func,
                "properties": properties,
                "required": required,
                "group": group,
            }
            return func

        return decorator

    def to_params(self, *, enabled_groups: Collection[str] = ()) -> list[ToolParam]:
        """转换为与格式无关的工具定义列表"""
        groups = set(enabled_groups)
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
            for name, info in self._registry.items()
            if info["group"] is None or info["group"] in groups
        ]

    async def execute(self, call: ToolCall, *, enabled_groups: Collection[str] = ()) -> str:
        """执行一次工具调用，返回交回模型的结果

        执行失败时返回错误描述而非抛出异常，让模型有机会自行调整。
        """
        info = self._registry.get(call.name)
        if not info:
            logger.warning("LLM 请求了未注册的工具")
            return f"错误：未注册的工具 {call.name}"
        if info["group"] is not None and info["group"] not in enabled_groups:
            logger.warning("LLM 请求了未启用的工具（工具={}，分组={}）", call.name, info["group"])
            return f"错误：当前未启用工具 {call.name}"

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

        output = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        logger.info(
            "LLM 工具执行完成（工具={}，结果字符={}，耗时={:.3f}s）",
            call.name,
            len(output),
            perf_counter() - started_at,
        )
        return output


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


registry = ToolRegistry()
"""全局工具注册表"""

# 内置工具在注册表创建后导入，避免模块初始化时的循环依赖。
from . import web as web
