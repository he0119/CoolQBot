"""普通插件可以在 PluginMetadata.extra 中声明的可选 LLM 工具。"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

BUSINESS_TOOLS_KEY = "coolqbot.llm_tools"


@dataclass(frozen=True)
class BusinessTool:
    name: str
    description: str
    function: "Callable[..., str | Awaitable[str]]"
