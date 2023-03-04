""" 藏宝选门 """
from typing import Literal

from nonebot.adapters import Message
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg, Depends
from nonebot.plugin import PluginMetadata

from ... import ff14
from .data_source import get_direction

__plugin_meta__ = PluginMetadata(
    name="藏宝选门",
    description="告诉我该选哪个门吧",
    usage="""选择门的数量
/gate 2
/gate 3""",
)

gate_cmd = ff14.command("gate", aliases={"gate"})


async def get_door_number(door_number: str = ArgPlainText()) -> int:
    """获取门的数量"""
    if not door_number:
        await gate_cmd.reject("你什么都不输入我怎么知道呢，请告诉我有几个门！")

    if not door_number.isdigit():
        await gate_cmd.reject("门的数量只能是数字！")

    number = int(door_number)
    if number not in [2, 3]:
        await gate_cmd.reject("暂时只支持两个门或者三个门的情况，请重新输入吧。")

    return number


@gate_cmd.handle()
async def gate_handle_first_receive(matcher: Matcher, arg: Message = CommandArg()):
    if arg.extract_plain_text():
        matcher.set_arg("door_number", arg)


@gate_cmd.got("door_number", prompt="总共有多少个门呢？")
async def gate_handle(door_number: Literal[2, 3] = Depends(get_door_number)):
    direction = get_direction(door_number)
    await gate_cmd.finish(direction, at_sender=True)
