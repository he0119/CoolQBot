from datetime import datetime
from typing import Optional

import httpx
from nonebot.adapters.cqhttp import Message

from src.utils.helpers import render_expression
from dateutil import parser
from .config import DATA


def get_first_connect_message():
    """ 根据当前时间返回对应消息 """
    hour = datetime.now().hour

    if hour > 18 or hour < 6:
        return '晚上好呀！'

    if hour > 13:
        return '下午好呀！'

    if hour > 11:
        return '中午好呀！'

    return '早上好呀！'


EXPR_MORNING = (
    '早上好呀~>_<~\n{message}',
    '大家早上好呀！\n{message}',
    '朋友们早上好！\n{message}',
    '群友们早上好！\n{message}',
 ) # yapf: disable


HOLIDAYS_DATA = DATA.network_file(
    'https://cdn.jsdelivr.net/gh/he0119/coolqbot@change/morning/src/plugins/morning/holidays.json',
    'holidays.json',
)


async def get_recent_holiday() -> Optional[dict[str, dict]]:
    """ 获取最近的节假日

    返回最近的节假日信息
    """
    now = datetime.now()
    # 提取所需要的数据，今年和明年的节日数据
    # 因为明年元旦的节假日可能从今年开始
    holidays = {}
    data = await HOLIDAYS_DATA.data
    if data:
        if str(now.year) in data:
            holidays.update(data[str(now.year)])
        if str(now.year + 1) in data:
            holidays.update(data[str(now.year + 1)])
    # 查找最近的节日
    for holiday in holidays:
        if parser.parse(holiday) > now:
            info = holidays[holiday]
            info['date'] = holiday
            return info


async def get_moring_message() -> Message:
    """ 获得早上问好

    日期不同，不同的问候语
    通过 [免费节假日 API](http://timor.tech/api/holiday/)
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
