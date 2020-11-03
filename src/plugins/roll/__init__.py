""" roll 点插件

NGA 风格 ROLL 点
掷骰子
"""
import re

from nonebot import on_command
from nonebot.typing import Bot, Event

from .rand import get_rand
from .roll import roll_dices

#region roll
roll_cmd = on_command('roll', block=True)
roll_cmd.__doc__ = """
roll

NGA 风格 ROLL 点

roll 一次点数100
/roll d100
roll 两次点数100和两次点数50
/roll 2d100+2d50
"""


@roll_cmd.handle()
async def _(bot: Bot, event: Event, state: dict):
    args = str(event.message).strip()

    # 检查是否符合规则
    match = re.match(r'^([\dd+\s]+?)$', args)

    if args and match:
        state['input'] = args


@roll_cmd.args_parser
async def _(bot: Bot, event: Event, state: dict):
    args = str(event.message).strip()

    # 检查是否符合规则
    match = re.match(r'^([\dd+\s]+?)$', args)

    if not args:
        await roll_cmd.reject('ROLL 点方式不能为空呢，请重新输入')

    if not match:
        await roll_cmd.reject('请输入正确的参数 ~>_<~')

    state[state['_current_key']] = args


@roll_cmd.got(
    'input',
    prompt='欢迎使用 NGA 风格 ROLL 点插件\n请问你想怎么 ROLL 点\n你可以输入 d100\n也可以输入 2d100+2d50'
)
async def _(bot: Bot, event: Event, state: dict):
    input_str = state['input']
    str_data = roll_dices(input_str)
    await roll_cmd.finish(str_data, at_sender=True)


#endregion
#region rand
rand_cmd = on_command('rand', block=True)
rand_cmd.__doc__ = """
rand

获得 0-100 的点数
/rand
获得一件事情的概率
/rand 今天捐钱的概率
"""


@rand_cmd.handle()
async def _(bot: Bot, event: Event, state: dict):
    args = str(event.message).strip()

    str_data = get_rand(args)
    await rand_cmd.finish(str_data, at_sender=True)


#endregion
