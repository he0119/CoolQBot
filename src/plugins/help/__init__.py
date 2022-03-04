""" 帮助

通过给命令 __doc__ 添加帮助信息实现
"""
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg

from .commands import get_command_help, get_command_list

help_cmd = on_command("help", aliases={"帮助"})
help_cmd.__doc__ = """
获取帮助

获取所有支持的命令
/help list
获取某个命令的帮助
/help 命令名
"""


@help_cmd.handle()
async def help_handle(args: Message = CommandArg()):
    plaintext = args.extract_plain_text().strip()

    if plaintext == "list":
        await help_cmd.finish(get_command_list())
    elif plaintext:
        command_help = get_command_help(plaintext)
        if command_help:
            await help_cmd.finish(command_help)
        await help_cmd.finish("请输入支持的命令")
    else:
        await help_cmd.finish(get_command_help("help"))
