""" 每日早安插件
"""
import re

import httpx
from nonebot import logger, on_command, scheduler, get_bot
from nonebot.helpers import render_expression

from coolqbot import PluginData

DATA = PluginData('morning', config=True)

HOUR = int(DATA.get_config('morning', 'hour', fallback='7'))
MINUTE = int(DATA.get_config('morning', 'minute', fallback='30'))
SECOND = int(DATA.get_config('morning', 'second', fallback='0'))


@scheduler.scheduled_job(
    'cron', hour=HOUR, minute=MINUTE, second=SECOND, id='morning'
)
async def morning():
    """ 早安
    """
    hello_str = await get_message()
    for group_id in get_bot().config.GROUP_ID:
        await get_bot().send_msg(
            message_type='group', group_id=group_id, message=hello_str
        )
    logger.info('发送早安信息')


EXPR_MORNING = [
    '早上好呀~>_<~\n{message}',
    '大家早上好呀！\n{message}',
    '朋友们早上好！\n{message}',
    '群友们早上好！\n{message}',
] # yapf: disable


async def get_message():
    """ 获得消息

    不同的问候语
    """
    try:
        # 获得不同的问候语
        async with httpx.AsyncClient() as client:
            r = await client.get('http://timor.tech/api/holiday/tts')
            rjson = r.json()
    except:
        rjson = {'code': -1}

    if rjson['code'] == 0:
        message = rjson['tts']
    else:
        message = '好像没法获得节假日信息了，嘤嘤嘤'

    return render_expression(EXPR_MORNING, message=message)
