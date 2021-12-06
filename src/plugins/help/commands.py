""" 命令信息

通过命令的 __doc__ 获取命令信息
"""
import inspect
from dataclasses import dataclass
from functools import reduce
from typing import Optional

from nonebot import get_driver, get_loaded_plugins
from nonebot.handler import Handler
from nonebot.matcher import Matcher
from nonebot.rule import Command


@dataclass
class CommandInfo:
    """命令的信息"""

    name: str
    aliases: list[str]
    help: str


_commands: Optional[list[CommandInfo]] = None


def extract_command_info(matcher: Matcher) -> Optional[CommandInfo]:
    """从 Matcher 中提取命令的数据"""
    checkers: set[Handler] = matcher.rule.checkers
    command_handler: Optional[Handler] = next(
        filter(lambda x: isinstance(x.call, Command), checkers), None
    )
    if not command_handler:
        return

    help = matcher.__doc__
    if help is None:
        return
    help = inspect.cleandoc(help)

    command: Command = command_handler.call
    # 确保英文名字在前，中文名字在后
    # 命令越长越靠前
    cmds: list[tuple[str]] = sorted(
        sorted(command.cmds), key=lambda x: len(x), reverse=True
    )

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
