""" 每日早安插件
"""
import httpx
from nonebot import get_bots, get_driver, logger, scheduler

from utils.helpers import render_expression

from .config import Config

morning_config = Config(**get_driver().config.dict())


@scheduler.scheduled_job(
    'cron',
    hour=morning_config.morning_hour,
    minute=morning_config.morning_minute,
    second=morning_config.morning_second,
    id='morning'
)
async def morning():
    """ 早安
    """
    hello_str = await get_message()
    await list(get_bots().values())[0].send_msg(
        message_type='group',
        group_id=get_driver().config.group_id,
        message=hello_str
    )
    logger.info('发送早安信息')


EXPR_MORNING = [
    '早上好呀~>_<~\n{message}',
    '大家早上好呀！\n{message}',
    '朋友们早上好！\n{message}',
    '群友们早上好！\n{message}',
] # yapf: disable


async def get_message() -> str:
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
