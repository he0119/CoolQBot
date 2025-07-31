"""藏宝选门"""

from typing import Literal, cast

from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension

from .data_source import get_direction

__plugin_meta__ = PluginMetadata(
    name="藏宝选门",
    description="告诉我该选哪个门吧",
    usage="""选择门的数量
/gate 2
/gate 3""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)

gate_cmd = on_alconna(
    Alconna(
        "gate",
        Args["door_number?#门的数量", str],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"藏宝选门", "选门"},
    use_cmd_start=True,
    block=True,
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh_CN": "藏宝选门"}),
    ],
)


@gate_cmd.handle()
async def gate_handle_first_receive(door_number: Match[str]):
    if door_number.available:
        gate_cmd.set_path_arg("door_number", door_number.result)


@gate_cmd.got_path("door_number", prompt="总共有多少个门呢？")
async def gate_handle(door_number: str):
    door_number = door_number.strip()

    if not door_number.isdigit():
        await gate_cmd.reject("门的数量只能是数字！")

    number = int(door_number)
    if number not in [2, 3]:
        await gate_cmd.reject("暂时只支持两个门或者三个门的情况，请重新输入吧。")

    number = cast("Literal[2, 3]", number)
    direction = get_direction(number)
    await gate_cmd.finish(direction, at_sender=True)
