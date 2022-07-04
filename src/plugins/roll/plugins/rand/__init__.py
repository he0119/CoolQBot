""" 掷骰子 """
from nonebot import on_command
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

from .data_source import get_rand

__plugin_meta__ = PluginMetadata(
    name="掷骰子",
    description="获得一个点数或者概率",
    usage="获得 0-100 的点数\n/rand\n获得一件事情的概率\n/rand 今天捐钱的概率",
)

rand_cmd = on_command("rand")


@rand_cmd.handle()
async def rand_handle(args: Message = CommandArg()):
    plaintext = args.extract_plain_text().strip()

    str_data = get_rand(plaintext)
    await rand_cmd.finish(str_data, at_sender=True)
