""" 帮助数据

获取插件的帮助信息，并通过子插件的形式获取二级菜单
"""
import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, cast

from nonebot import get_loaded_plugins
from nonebot.rule import CommandRule

if TYPE_CHECKING:
    from nonebot.matcher import Matcher
    from nonebot.plugin import Plugin


@dataclass
class CommandInfo:
    """命令的信息"""

    name: str
    aliases: list[str]
    help: str


_plugins: Optional[dict[str, "Plugin"]] = None


def sort_commands(cmds: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
    """排序命令

    确保英文名字在前，中文名字在后
    命令越长越靠前
    """
    return sorted(
        cmds,
        key=lambda x: (
            len("".join(x).encode("ascii", "ignore")),  # 英文在前
            len(x),  # 命令越长越靠前
            len("".join(x)),  # 命令字数越长越靠前
        ),
        reverse=True,
    )


def extract_command_info(matcher: "Matcher") -> Optional[CommandInfo]:
    """从 Matcher 中提取命令的数据"""
    checkers = matcher.rule.checkers
    command_handler = next(
        filter(lambda x: isinstance(x.call, CommandRule), checkers), None
    )
    if not command_handler:
        return

    help = matcher.__doc__
    if help is None:
        return
    help = inspect.cleandoc(help)

    command = cast(CommandRule, command_handler.call)
    cmds = sort_commands(command.cmds)

    name = ".".join(cmds[0])
    if len(cmds) > 1:
        aliases = list(map(lambda x: ".".join(x), cmds[1:]))
    else:
        aliases = []
    return CommandInfo(name=name, aliases=aliases, help=help)


def get_plugins() -> dict[str, "Plugin"]:
    global _plugins
    if _plugins is None:
        # 仅获取适配了元信息的插件
        plugins = filter(lambda x: x.metadata is not None, get_loaded_plugins())
        _plugins = {x.metadata.name: x for x in plugins}  # type: ignore
    return _plugins


def get_plugin_list() -> str:
    # 仅获取适配了元信息的插件
    plugins = get_plugins()

    docs = "插件列表：\n"
    docs += "\n".join(
        sorted(
            map(
                lambda x: f"{x.metadata.name} # {x.metadata.description}",  # type: ignore
                plugins.values(),
            )
        )
    )
    return docs


def get_plugin_help(name: str) -> Optional[str]:
    """通过插件获取命令的帮助"""
    plugins = get_plugins()

    plugin = plugins.get(name)
    if plugin:
        return f"{name}\n\n{plugin.metadata.usage}"  # type: ignore
    else:
        return None
