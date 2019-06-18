""" 藏宝选门
"""
import re
from random import randint

from nonebot import CommandSession, on_command

TEXTS = [
    '掐指一算，你应该走[direction]！',
    '夜观天象，你应该走[direction]！',
    '冷静分析，你应该走[direction]！',
    '一拍大腿，你应该走[direction]！',
    '我寻思，走[direction]一定可以到7层',
    '想了想，走[direction]应该是最好的选择！',
    '走[direction]，准没错！难道你不相信可爱的小誓约吗！',
    '投了个硬币，仔细一看，走[direction]。不信我，难道你还不信硬币么！',
    '直觉告诉我，你走[direction]就会马上出去......'
]


@on_command('gate', only_to_me=False)
async def gate(session: CommandSession):
    door_number = session.get('door_number', prompt='总共有多少个门呢？')

    text_index = randint(0, len(TEXTS) - 1)

    direction = get_direction(int(door_number))

    await session.send(TEXTS[text_index].replace('[direction]', direction),
                       at_sender=True)


@gate.args_parser
async def _(session: CommandSession):
    stripped_arg = session.current_arg_text.strip()

    if session.is_first_run:
        if stripped_arg:
            session.state['door_number'] = stripped_arg
        return

    if not stripped_arg:
        session.pause('你什么都不输入我怎么知道呢，请告诉我有几个门！')
    if stripped_arg not in ['2', '3']:
        session.pause('暂时只支持两个门或者三个门的情况，请重新输入吧。')

    session.state[session.current_key] = stripped_arg


def get_direction(door_number):
    if door_number == 2:
        if randint(1, 2) == 1:
            return '左边'
        return '右边'
    elif door_number == 3:
        rand = randint(1, 3)
        if rand == 1:
            return '左边'
        elif rand == 2:
            return '中间'
        return '右边'
