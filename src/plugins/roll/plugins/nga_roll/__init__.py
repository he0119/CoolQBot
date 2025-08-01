"""ROLL 点"""

import re

from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension

from .data_source import roll_dices

__plugin_meta__ = PluginMetadata(
    name="ROLL 点",
    description="NGA 风格 ROLL 点",
    usage="""roll 一次点数100
/roll d100
roll 两次点数100和两次点数50
/roll 2d100+2d50""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)

roll_cmd = on_alconna(
    Alconna(
        "roll",
        Args["input?#ROLL 点方式", str],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    use_cmd_start=True,
    block=True,
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(),
    ],
)


def check_roll_syntax(input: str) -> bool:
    """检查是否符合规则"""
    match = re.match(r"^([\dd+\s]+?)$", input)
    return bool(match)


@roll_cmd.handle()
async def roll_handle_first_receive(input: Match[str]):
    if input.available:
        roll_cmd.set_path_arg("input", input.result)


@roll_cmd.got_path(
    "input",
    prompt="欢迎使用 NGA 风格 ROLL 点插件\n请问你想怎么 ROLL 点\n你可以输入 d100\n也可以输入 2d100+2d50",
)
async def roll_handle(input: str):
    if not check_roll_syntax(input):
        await roll_cmd.reject("请输入正确的参数 ~>_<~")

    str_data = roll_dices(input)
    await roll_cmd.finish(str_data, at_sender=True)
