""" 掷骰子
"""
import re
from random import randint

from nonebot import CommandSession, on_command


@on_command('rand', only_to_me=False)
async def rand(session: CommandSession):
    text = session.get('text', prompt='请问你想知道什么的概率？')

    str_data = ''
    probability = re.match(r'^.+(可能性|几率|概率)$', text)
    if probability:
        str_data += text
        str_data += '是 '
        str_data += str(randint(0, 100))
        str_data += '%'
    else:
        str_data += ' 你的点数是 '
        str_data += str(randint(0, 100))

    await session.send(str_data)


@rand.args_parser
async def _(session: CommandSession):
    stripped_arg = session.current_arg_text.strip()

    if session.is_first_run:
        session.state['text'] = stripped_arg
        return

    session.state[session.current_key] = stripped_arg
