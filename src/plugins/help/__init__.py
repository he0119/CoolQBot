""" 帮助 """
import inspect
from dataclasses import dataclass
from functools import reduce
from typing import List, Optional

from nonebot import get_loaded_plugins, on_command
from nonebot.rule import command
from nonebot.typing import Bot, Event


@dataclass
class CommandInfo:
    """ 命令的信息 """
    name: str
    help: str


_commands: Optional[List[CommandInfo]] = None


def extract_command_info(doc: str) -> CommandInfo:
    """ 提取 __doc__ 中的数据 """
    lines = doc.splitlines()
    name = lines[0]
    help = '\n'.join(lines[2:])
    return CommandInfo(name=name, help=help)


def get_commands() -> List[CommandInfo]:
    """ 获取所有命令的信息

    并保存，方便下次使用
    """
    global _commands
    if _commands is None:
        plugins = get_loaded_plugins()
        matchers = reduce(lambda x, y: x.union(y.matcher), plugins, set())
        matcher_docs = list(
            map(
                lambda x: inspect.cleandoc(x.__doc__),
                filter(lambda x: x.__doc__, matchers)
            )
        )
        _commands = list(map(extract_command_info, matcher_docs))
    return _commands


def get_commands_name() -> List[str]:
    """ 获取所有命令的名字 """
    commands = get_commands()
    return list(map(lambda x: x.name, commands))


def get_command_help(name: str) -> str:
    """ 通过命令名字获取命令的帮助 """
    commands = get_commands()
    commands = list(filter(lambda x: x.name == name, commands))
    if commands:
        return commands[0].help
    else:
        return None


help = on_command('help', aliases={'帮助'}, priority=1, block=True)
help.__doc__ = """
help

获取帮助

获取所有支持的命令
/help all
获取某个命令的帮助
/help <cmd>
"""


@help.handle()
async def handle(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()
    if stripped_arg == 'all':
        docs = "命令列表：\n"
        docs += "\n".join(get_commands_name())
        await help.finish(docs)
    elif stripped_arg:
        command_help = get_command_help(stripped_arg)
        if command_help:
            await help.finish(command_help)
        await help.finish('请输入支持的命令')
    else:
        await help.finish(get_command_help('help'))
