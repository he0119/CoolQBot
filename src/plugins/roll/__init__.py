""" roll 点插件

NGA 风格 ROLL 点
掷骰子
"""
import re

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg, Depends

from .rand import get_rand
from .roll import roll_dices

# region roll
roll_cmd = on_command("roll", block=True)
roll_cmd.__doc__ = """
NGA 风格 ROLL 点

roll 一次点数100
/roll d100
roll 两次点数100和两次点数50
/roll 2d100+2d50
"""


def check_roll_syntax(input: str) -> bool:
    """检查是否符合规则"""
    match = re.match(r"^([\dd+\s]+?)$", input)
    return bool(match)


@roll_cmd.handle()
async def roll_handle_first_receive(matcher: Matcher, arg: Message = CommandArg()):
    input = arg.extract_plain_text()

    # 如果有输入，则直接检查，出错就直接提示并结束对话
    if input and not check_roll_syntax(input):
        await roll_cmd.finish("请输入正确的参数 ~>_<~")
    if input:
        matcher.set_arg("input", arg)


async def get_roll_input(input: str = ArgPlainText()) -> str:
    """检查输入是否能满足要求"""
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


# endregion
# region rand
rand_cmd = on_command("rand", block=True)
rand_cmd.__doc__ = """
掷骰子/概率

获得 0-100 的点数
/rand
获得一件事情的概率
/rand 今天捐钱的概率
"""


@rand_cmd.handle()
async def rand_handle(arg: Message = CommandArg()):
    str_data = get_rand(arg.extract_plain_text())
    await rand_cmd.finish(str_data, at_sender=True)


# endregion
