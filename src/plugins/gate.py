""" 藏宝选门
"""
import re
from random import randint

from coolqbot.bot import bot

TEXTS = ['掐指一算，你应该走[direction]！',
         '夜观天象，你应该走[direction]！',
         '冷静分析，你应该走[direction]！',
         '一拍大腿，你应该走[direction]！',
         '我寻思，走[direction]一定可以到7层',
         '想了想，走[direction]应该是最好的选择！',
         '走[direction]，准没错！难道你不相信可爱的小誓约吗！',
         '投了个硬币，仔细一看，走[direction]。不信我，难道你还不信硬币么！',
         '直觉告诉我，你走[direction]就会马上出去......']


@bot.on_message('group', 'private')
async def gate(context):
    match = re.match(r'^\/gate ?(\w*)?', context['message'])
    if match:
        args = match.group(1)

        door_number = 2
        if args == '3':
            door_number = 3

        text_index = randint(0, len(TEXTS)-1)

        direction = get_direction(door_number)

        return {'reply': TEXTS[text_index].replace('[direction]', direction)}


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
