""" NGA 风格 ROLL 点插件
"""
import re
from random import randint

from nonebot import CommandSession, on_command


@on_command('roll', only_to_me=False)
async def roll(session: CommandSession):
    args = session.get(
        'args',
        prompt=
        '欢迎使用 NGA 风格 ROLL 点插件\n请问你想怎么 ROLL 点\n你可以输入 d100\n也可以输入 2d100+2d50')
    str_data = roll_dices(args)

    await session.send(str_data)


@roll.args_parser
async def _(session: CommandSession):
    stripped_arg = session.current_arg_text.strip()

    # 检查是否符合规则
    match = re.match(r'^([\dd+\s]+?)$', stripped_arg)

    if session.is_first_run:
        if stripped_arg and match:
            session.state['args'] = stripped_arg
        return

    if not stripped_arg:
        session.pause('ROLL 点方式不能为空呢，请重新输入')

    if not match:
        session.pause('请输入正确的参数 ~>_<~')
    session.state[session.current_key] = stripped_arg


def roll_dices(input_str):
    """ 掷骰子
    """
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
