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
roll = on_command('roll', priority=1, block=True)


@roll.handle()
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    # 检查是否符合规则
    match = re.match(r'^([\dd+\s]+?)$', stripped_arg)

    if stripped_arg and match:
        state['input'] = stripped_arg


@roll.args_parser
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    # 检查是否符合规则
    match = re.match(r'^([\dd+\s]+?)$', stripped_arg)

    if not stripped_arg:
        await roll.reject('ROLL 点方式不能为空呢，请重新输入')

    if not match:
        await roll.reject('请输入正确的参数 ~>_<~')

    state['input'] = stripped_arg


@roll.got(
    'input',
    prompt='欢迎使用 NGA 风格 ROLL 点插件\n请问你想怎么 ROLL 点\n你可以输入 d100\n也可以输入 2d100+2d50'
)
async def _(bot: Bot, event: Event, state: dict):
    input_str = state['input']
    str_data = roll_dices(input_str)
    await roll.finish(str_data, at_sender=True)


#endregion
#region rand
rand = on_command('rand', priority=1, block=True)


@rand.handle()
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()
    str_data = get_rand(stripped_arg)
    await rand.finish(str_data, at_sender=True)


#endregion
