""" NGA风格ROLL点插件
"""
import re
from random import randint

from coolqbot.bot import bot


@bot.on_message('group', 'private')
async def roll(context):
    match = re.match(r'^\/roll(?: (.*))?$', context['message'])
    if match:
        args = match.group(1)

        if args:
            str_data = roll_dices(args)
        else:
            str_data = '欢迎使用 NGA 风格 ROLL 点插件\n你可以 /roll d100\n也可以 /roll 2d100+2d50'

        return {'reply': str_data, 'at_sender': False}


def roll_dices(input_str):
    """ 掷骰子
    """
    match = re.match(r'^([\dd+\s]+?)$', input_str)
    if not match:
        return '请输入正确的参数~>_<~'
    r = ''
    add = 0
    input_str = '+' + input_str
    dices = re.findall(r'(\+)(\d{0,10})(?:(d)(\d{1,10}))?', input_str)
    raw_str = ''
    for dice in dices:
        dice_str, add = roll_single(dice, add)
        r += dice_str
        raw_str += f'{dice[0]}{dice[1]}{dice[2]}{dice[3]}'
    return f'{raw_str}={r}={add}' [1:].replace('=+', '=')


def roll_single(args, add):
    """ 掷一次
    """
    s1 = args[1]
    s2 = args[2]
    if s1:
        s1 = int(s1)
    elif s2:
        s1 = 1
    else:
        s1 = 0
    r = ''
    if not s2:
        add += s1
        return '+' + str(s1), add
    s3 = int(args[3])
    for dummy in range(s1):
        rand = randint(1, s3)
        r += '+d' + str(s3) + '(' + str(rand) + ')'
        add += rand
    return r, add
