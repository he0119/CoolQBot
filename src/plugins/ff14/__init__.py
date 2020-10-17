""" 最终幻想XIV

各种小工具
"""
from nonebot import on_command
from nonebot.typing import Bot, Event

from .gate import get_direction

#region 藏宝选门
gate = on_command(
    'gate',
    priority=1,
    block=True,
)


@gate.args_parser
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    if not stripped_arg:
        await gate.reject('你什么都不输入我怎么知道呢，请告诉我有几个门！')

    if stripped_arg not in ['2', '3']:
        await gate.reject('暂时只支持两个门或者三个门的情况，请重新输入吧。')

    state['door_number'] = int(stripped_arg)


@gate.handle()
async def handle_first_gate(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()
    if stripped_arg in ['2', '3']:
        state['door_number'] = int(stripped_arg)


@gate.got('door_number', prompt='总共有多少个门呢？')
async def handle_gate(bot: Bot, event: Event, state: dict):
    direction = get_direction(state['door_number'])
    await gate.finish(direction)


#endregion
