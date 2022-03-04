""" 命令信息

通过命令的 __doc__ 获取命令信息
"""
import inspect
from dataclasses import dataclass
from functools import reduce
from typing import Optional, cast

from nonebot import get_loaded_plugins
from nonebot.dependencies import Dependent
from nonebot.matcher import Matcher
from nonebot.rule import CommandRule


@dataclass
class CommandInfo:
    """命令的信息"""

    name: str
    aliases: list[str]
    help: str


_commands: Optional[list[CommandInfo]] = None


def extract_command_info(matcher: Matcher) -> Optional[CommandInfo]:
    """从 Matcher 中提取命令的数据"""
    checkers: set[Dependent] = matcher.rule.checkers
    command_handler: Optional[Dependent] = next(
        filter(lambda x: isinstance(x.call, CommandRule), checkers), None
    )
    if not command_handler:
        return

    help = matcher.__doc__
    if help is None:
        return
    help = inspect.cleandoc(help)

    command = cast(CommandRule, command_handler.call)
    # 确保英文名字在前，中文名字在后
    # 命令越长越靠前
    cmds: list[tuple[str]] = sorted(command.cmds)

    name = ".".join(cmds[0])
    if len(cmds) > 1:
        aliases = list(map(lambda x: ".".join(x), cmds[1:]))
    else:
        aliases = []
    return CommandInfo(name=name, aliases=aliases, help=help)


def get_commands() -> list[CommandInfo]:
    """获取所有命令的信息

    并保存，方便下次使用
    """
    global _commands
    if _commands is None:
        plugins = get_loaded_plugins()
        matchers = reduce(lambda x, y: x.union(y.matcher), plugins, set())
        commands = []
        for matcher in matchers:
            command = extract_command_info(matcher)
            if command:
                commands.append(command)
        _commands = commands
    return _commands


def get_command_help(name: str) -> Optional[str]:
    """通过命令名字获取命令的帮助"""
    commands = get_commands()
    command = next(
        filter(lambda x: x.name == name or name in x.aliases, commands), None
    )
    if command:
        return command.help
    else:
        return None


def format_name_aliases(command: CommandInfo) -> str:
    """格式化命令名称"""
    if command.aliases:
        return f'{command.name}({", ".join(command.aliases)})'
    else:
        return command.name


def get_command_list() -> str:
    commands = get_commands()
    docs = "命令（别名）列表：\n"
    docs += "\n".join(sorted(map(format_name_aliases, commands)))
    return docs
