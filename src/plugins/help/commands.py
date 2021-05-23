""" 命令信息

通过命令的 __doc__ 获取命令信息
"""
import inspect
from dataclasses import dataclass
from functools import reduce
from typing import List, Optional

from nonebot import get_loaded_plugins


@dataclass
class CommandInfo:
    """ 命令的信息 """
    name: str
    aliases: List[str]
    help: str


_commands: Optional[List[CommandInfo]] = None


def extract_command_info(doc: str) -> CommandInfo:
    """ 提取 __doc__ 中的数据 """
    lines = doc.splitlines()
    names = lines[0].split()
    name = names[0]
    aliases = []
    if len(names) > 1:
        aliases = names[1:]
    help = '\n'.join(lines[2:])
    return CommandInfo(name=name, aliases=aliases, help=help)


def get_commands() -> List[CommandInfo]:
    """ 获取所有命令的信息

    并保存，方便下次使用
    """
    global _commands
    if _commands is None:
        plugins = get_loaded_plugins()
        matchers = reduce(lambda x, y: x.union(y.matcher), plugins, set())
        matcher_docs = list(
            map(lambda x: inspect.cleandoc(x.__doc__),
                filter(lambda x: x.__doc__, matchers)))
        _commands = list(map(extract_command_info, matcher_docs))
    return _commands


def get_command_help(name: str) -> Optional[str]:
    """ 通过命令名字获取命令的帮助 """
    commands = get_commands()
    commands = list(
        filter(lambda x: x.name == name or name in x.aliases, commands))
    if commands:
        return commands[0].help
    else:
        return None
