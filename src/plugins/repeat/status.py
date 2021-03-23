""" 运行状态
"""
from datetime import datetime
from typing import Optional

from dateutil.relativedelta import relativedelta

from .recorder import recorder


def get_status(group_id: Optional[int]) -> str:
    """ 获取机器人运行状态，具体如下

    近十分钟群内聊天数量
    今日群内聊天总数
    本月群内聊天总数
    复读概率
    在线时间
    """
    str_data = ''
    if group_id:
        str_data = f'近十分钟群内聊天数量是 {recorder.message_number(10, group_id)} 条'

        repeat_num = get_total_number(recorder.repeat_list(group_id))
        msg_num = get_total_number(recorder.msg_number_list(group_id))
        today_msg_num = get_total_number(
            recorder.msg_number_list_by_day(datetime.now().day, group_id))

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
    return str_data.strip()


def get_total_number(record_list):
    """ 获取总数 """
    num = 0
    for _, v in record_list.items():
        num += v
    return num
