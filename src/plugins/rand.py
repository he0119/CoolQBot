""" 掷骰子
"""
import re
from random import randint

from coolqbot.bot import bot


@bot.on_message('group', 'private')
async def rand(context):
    match = re.match(r'\/rand(?: (.*)?)?', context['message'])
    if match:
        text = match.group(1)
        str_data = ''

        if not text:
            text = ''

        probability = re.match(r'.+(可能性|几率|概率)$', text)
        if probability:
            str_data += text
            str_data += '是 '
            str_data += str(randint(0, 100))
            str_data += '%'
        else:
            str_data += ' 你的点数是 '
            str_data += str(randint(0, 100))

        return {'reply': str_data}
