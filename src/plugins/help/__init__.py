""" 帮助 """
from nonebot import on_command
from nonebot.typing import Bot, Event

from src.utils.commands import CommandInfo, get_command_help, get_commands

help = on_command('help', aliases={'帮助'}, priority=1, block=True)
help.__doc__ = """
help 帮助

获取帮助

获取所有支持的命令
/help all
获取某个命令的帮助
/help <cmd>
"""


def format_name_aliases(command: CommandInfo) -> str:
    """ 格式化命令名称 """
    if command.aliases:
        return f'{command.name}({", ".join(command.aliases)})'
    else:
        return command.name


@help.handle()
async def handle(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()
    if stripped_arg == 'all':
        commands = get_commands()
        docs = "命令（别名）列表：\n"
        docs += "\n".join(sorted(map(format_name_aliases, commands)))
        await help.finish(docs)
    elif stripped_arg:
        command_help = get_command_help(stripped_arg)
        if command_help:
            await help.finish(command_help)
        await help.finish('请输入支持的命令')
    else:
        await help.finish(get_command_help('help'))
