""" 每日早安插件
"""
import re

import requests
from nonebot import on_command
from nonebot.helpers import render_expression

from coolqbot import PluginData, bot

DATA = PluginData('morning', config=True)

HOUR = int(DATA.config_get('morning', 'hour', fallback='7'))
MINUTE = int(DATA.config_get('morning', 'minute', fallback='30'))
SECOND = int(DATA.config_get('morning', 'second', fallback='0'))


@bot.scheduler.scheduled_job(
    'cron', hour=HOUR, minute=MINUTE, second=SECOND, id='morning'
)
async def morning():
    """ 早安
    """
    hello_str = get_message()
    for group_id in bot.get_bot().config.GROUP_ID:
        await bot.get_bot().send_msg(
            message_type='group', group_id=group_id, message=hello_str
        )
    bot.logger.info('发送早安信息')


EXPR_MORNING = [
    '早上好呀~>_<~\n{message}',
    '大家早上好呀！\n{message}',
    '朋友们早上好！\n{message}',
    '群友们早上好！\n{message}',
] # yapf: disable


def get_message():
    """ 获得消息

    不同的问候语
    """
    try:
        # 获得不同的问候语
        res = requests.get('http://timor.tech/api/holiday/tts').json()
    except:
        res = {'code': -1}

    if res['code'] == 0:
        message = res['tts']
    else:
        message = '好像没法获得节假日信息了，嘤嘤嘤'

    return render_expression(EXPR_MORNING, message=message)
