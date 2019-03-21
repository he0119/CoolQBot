""" 每日早安插件
"""
import re
from random import randint

import requests

from coolqbot.bot import bot
from coolqbot.config import GROUP_ID
from coolqbot.utils import scheduler


@scheduler.scheduled_job('cron', hour=8, minute=0, second=0)
async def morning():
    """ 早安
    """
    hello_str = get_message()
    await bot.send_msg(message_type='group', group_id=GROUP_ID, message=hello_str)
    bot.logger.info('发送问好信息')


TEXTS = ['早上好呀~>_<~',
         '大家早上好呀！',
         '朋友们早上好！',
         '圆神的信徒们早上好~']


def get_message():
    """ 获得消息

    不同的问候语
    """
    try:
        # 获得不同的问候语
        res = requests.get('http://timor.tech/api/holiday/tts').json()
    except:
        res = {'code': -1}

    text_index = randint(0, len(TEXTS)-1)
    str_data = f'{TEXTS[text_index]}\n'

    if res['code'] == 0:
        str_data += res["tts"]
    else:
        str_data += '好像没法获得节假日信息了，嘤嘤嘤'

    return str_data
