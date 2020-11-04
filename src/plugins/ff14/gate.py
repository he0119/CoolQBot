""" 藏宝选门 """
from random import randint

from src.utils.helpers import render_expression

EXPR_GATE = (
    '掐指一算，你应该走{direction}！',
    '夜观天象，你应该走{direction}！',
    '冷静分析，你应该走{direction}！',
    '一拍大腿，你应该走{direction}！',
    '我寻思，走{direction}一定可以到最底层！',
    '想了想，走{direction}应该是最好的选择！',
    '走{direction}，准没错！难道你不相信可爱的小誓约吗！',
    '投了个硬币，仔细一看，走{direction}。不信我，难道你还不信硬币么！',
    '直觉告诉我，你走{direction}就会马上出去......',
    '千万不要走{direction}，会马上出去的！',
) # yapf: disable


def get_direction(door_number: int) -> str:
    direction = ''
    if door_number == 2:
        if randint(1, 2) == 1:
            direction = '左边'
        direction = '右边'
    elif door_number == 3:
        rand = randint(1, 3)
        if rand == 1:
            direction = '左边'
        elif rand == 2:
            direction = '中间'
        direction = '右边'
    return render_expression(EXPR_GATE, direction=direction)
