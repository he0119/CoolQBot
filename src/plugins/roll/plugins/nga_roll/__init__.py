""" ROLL 点 """
import re

from nonebot import on_command
from nonebot.adapters import Message
from nonebot.params import Arg, CommandArg, Depends
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from .data_source import roll_dices

__plugin_meta__ = PluginMetadata(
    name="ROLL 点",
    description="NGA 风格 ROLL 点",
    usage="""roll 一次点数100
/roll d100
roll 两次点数100和两次点数50
/roll 2d100+2d50""",
)

roll_cmd = on_command("roll", block=True)


def check_roll_syntax(input: str) -> bool:
    """检查是否符合规则"""
    match = re.match(r"^([\dd+\s]+?)$", input)
    return bool(match)


@roll_cmd.handle()
async def roll_handle_first_receive(state: T_State, args: Message = CommandArg()):
    plaintext = args.extract_plain_text().strip()

    # 如果有输入，则直接检查，出错就直接提示并结束对话
    if plaintext and not check_roll_syntax(plaintext):
        await roll_cmd.finish("请输入正确的参数 ~>_<~")

    if plaintext:
        state["input"] = plaintext


async def get_roll_input(input: str | Message = Arg()) -> str:
    """检查输入是否能满足要求"""
    if isinstance(input, Message):
        input = input.extract_plain_text().strip()

    if not input:
        await roll_cmd.reject("ROLL 点方式不能为空呢，请重新输入")

    if not check_roll_syntax(input):
        await roll_cmd.reject("请输入正确的参数 ~>_<~")

    return input


@roll_cmd.got(
    "input",
    prompt="欢迎使用 NGA 风格 ROLL 点插件\n请问你想怎么 ROLL 点\n你可以输入 d100\n也可以输入 2d100+2d50",
)
async def roll_handle(input: str = Depends(get_roll_input)):
    str_data = roll_dices(input)
    await roll_cmd.finish(str_data, at_sender=True)
