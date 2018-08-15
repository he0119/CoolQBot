'''NGA风格ROLL点插件'''
import re
from random import randint

from coolqbot.bot import bot
from coolqbot.logger import logger


@bot.on_message('group', 'private')
async def roll(context):
    match = re.match(r'^\/roll ?(.*)?$', context['message'])
    if match:
        str_data = roll_dices(match.group(1))
        return {'reply': str_data, 'at_sender': False}


def roll_dices(raw_string):
    '''掷骰子'''
    match = re.match(r'^([\dd+\s]+?)$', raw_string)
    if not match:
        return '请输入正确的参数~>_<~'
    r = ''
    add = 0
    s1 = '+' + raw_string
    dices = re.findall(r'(\+)(\d{0,10})(?:(d)(\d{1,10}))?', s1)
    for dice in dices:
        dice_str, add = roll_single(dice, add)
        r += dice_str
    return f'{raw_string}={r}={add}'.replace('=+', '=')


def roll_single(args, add):
    '''掷一次'''
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
