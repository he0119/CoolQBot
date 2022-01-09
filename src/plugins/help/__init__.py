""" 帮助

通过给命令 __doc__ 添加帮助信息实现
"""
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg

from .commands import CommandInfo, get_command_help, get_commands

help_cmd = on_command("help", aliases={"帮助"})
help_cmd.__doc__ = """
获取帮助

获取所有支持的命令
/help all
获取某个命令的帮助
/help 命令名
"""


def format_name_aliases(command: CommandInfo) -> str:
    """格式化命令名称"""
    if command.aliases:
        return f'{command.name}({", ".join(command.aliases)})'
    else:
        return command.name


@help_cmd.handle()
async def help_handle(arg: Message = CommandArg()):
    args = arg.extract_plain_text()

    if args == "all":
        commands = get_commands()
        docs = "命令（别名）列表：\n"
        docs += "\n".join(sorted(map(format_name_aliases, commands)))
        await help_cmd.finish(docs)
    elif args:
        command_help = get_command_help(args)
        if command_help:
            await help_cmd.finish(command_help)
        await help_cmd.finish("请输入支持的命令")
    else:
        await help_cmd.finish(get_command_help("help"))
