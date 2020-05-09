""" 运行状态
"""
import re
from datetime import datetime

import aiocqhttp
from dateutil.relativedelta import relativedelta
from nonebot import CommandSession, get_bot, logger, on_websocket_connect

from .recorder import recorder


async def get_status(session: CommandSession):
    """ 获取状态 """
    group_id = session.ctx['group_id']
    str_data = f'近十分钟群内聊天数量是 {recorder.message_number(10, group_id)} 条'

    repeat_num = get_total_number(recorder.repeat_list(group_id))
    msg_num = get_total_number(recorder.msg_number_list(group_id))
    today_msg_num = get_total_number(
        recorder.msg_number_list_by_day(datetime.now().day, group_id)
    )

    if msg_num:
        repeat_rate = repeat_num / msg_num
    else:
        repeat_rate = 0

    str_data += f'\n今日群内聊天总数是 {today_msg_num} 条'
    str_data += f'\n本月群内聊天总数是 {msg_num} 条'
    str_data += f'\n复读概率是 {repeat_rate*100:.2f}%'

    # 距离第一次启动之后经过的时间
    rdate = relativedelta(datetime.now(), recorder.start_time)
    str_data += f'\n已在线'
    if rdate.years:
        str_data += f' {rdate.years} 年'
    if rdate.months:
        str_data += f' {rdate.months} 月'
    if rdate.days:
        str_data += f' {rdate.days} 天'
    if rdate.hours:
        str_data += f' {rdate.hours} 小时'
    if rdate.minutes:
        str_data += f' {rdate.minutes} 分钟'
    if rdate.seconds:
        str_data += f' {rdate.seconds} 秒'
    await session.send(str_data)


def get_total_number(record_list):
    """ 获取总数
    """
    num = 0
    for dummy, v in record_list.items():
        num += v
    return num


@on_websocket_connect
async def check_status(event: aiocqhttp.Event):
    """ 启动时发送问好信息 """
    hello_str = get_message()
    for group_id in get_bot().config.GROUP_ID:
        await get_bot().send_msg(
            message_type='group', group_id=group_id, message=hello_str
        )
    logger.info('发送首次启动的问好信息')


def get_message():
    """ 根据当前时间返回对应消息 """
    hour = datetime.now().hour

    if hour > 18 or hour < 6:
        return '晚上好呀！'

    if hour > 13:
        return '下午好呀！'

    if hour > 11:
        return '中午好呀！'

    return '早上好呀！'
