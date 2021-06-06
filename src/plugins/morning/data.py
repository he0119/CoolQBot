import json
from datetime import datetime

import httpx
from nonebot.adapters.cqhttp import Message
from nonebot.log import logger

from src.utils.helpers import render_expression

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


holidays: list = []


async def load_data_from_repo():
    """ 从仓库获取数据 """
    logger.info('正在加载仓库数据')

    global holidays
    async with httpx.AsyncClient() as client:
        r = await client.get(
            'https://cdn.jsdelivr.net/gh/he0119/coolqbot@change/morning/src/plugins/morning/holidays.json',
            timeout=30)
        if r.status_code != 200:
            logger.error('仓库数据加载失败')
            return
        rjson = r.json()
        logger.info('仓库数据加载成功')
        # 同时保存一份文件在本地，以后就不用从网络获取
        with DATA.open('holidays.json', open_mode='w', encoding='utf8') as f:
            json.dump(rjson, f, ensure_ascii=False, indent=2)
            logger.info('已保存数据至本地')


async def load_data_from_local():
    """ 从本地获取数据 """
    logger.info('正在加载本地数据')

    global holidays
    if DATA.exists('holidays.json'):
        with DATA.open('holidays.json', encoding='utf8') as f:
            data = json.load(f)
            logger.info('本地数据加载成功')
    else:
        logger.info('本地数据不存在')


async def load_data():
    """ 加载数据

    先从本地加载，如果失败则从仓库加载
    """
    if not holidays:
        await load_data_from_local()
    if not holidays:
        await load_data_from_repo()


async def update_data():
    """ 从网络更新数据 """
    await load_data_from_repo()



EXPR_MORNING = (
    '早上好呀~>_<~\n{message}',
    '大家早上好呀！\n{message}',
    '朋友们早上好！\n{message}',
    '群友们早上好！\n{message}',
 ) # yapf: disable


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
