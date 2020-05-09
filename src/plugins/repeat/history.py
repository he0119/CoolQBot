""" 历史记录
"""
import re
from calendar import monthrange
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from nonebot import CommandSession, logger, scheduler

from . import DATA
from .rank import Ranking
from .recorder import Recorder, get_history_pkl_name, recorder


@scheduler.scheduled_job(
    'cron', day=1, hour=0, minute=0, second=0, id='clear_data'
)
async def clear_data():
    """ 每个月最后一天 24 点（下月 0 点）保存记录于历史记录文件夹，并重置记录
    """
    # 保存数据到历史文件夹
    date = datetime.now() - timedelta(hours=1)
    DATA.save_pkl(recorder.get_data(), get_history_pkl_name(date))
    # 清除现有数据
    recorder.init_data()
    logger.info('记录清除完成')


async def get_history(session: CommandSession):
    """ 获取历史数据 """
    year = session.get('year', prompt='你请输入你要查询的年份')
    month = session.get('month', prompt='你请输入你要查询的月份')
    day = session.get('day', prompt='你请输入你要查询的日期（如查询整月排名请输入 0）')

    str_data = ''
    now = datetime.now()
    is_valid, message = is_valid_date(year, month, day, now)
    if not is_valid:
        return message
    date = datetime(year=year, month=month, day=1)

    group_id = session.ctx['group_id']
    # 尝试读取历史数据
    # 如果是本月就直接从 recorder 中获取数据
    # 不是则从历史记录中获取
    if year == now.year and month == now.month:
        history_data = recorder
    else:
        history_filename = get_history_pkl_name(date)
        if not DATA.exists(f'{history_filename}.pkl'):
            if day:
                str_data = f'{date.year} 年 {date.month} 月 {day} 日的数据不存在，请换个试试吧 ~>_<~'
            else:
                str_data = f'{date.year} 年 {date.month} 月的数据不存在，请换个试试吧 0.0'
            return str_data
        history_data = Recorder(history_filename)

    if day:
        repeat_list = history_data.repeat_list_by_day(day, group_id)
        msg_number_list = history_data.msg_number_list_by_day(day, group_id)
    else:
        repeat_list = history_data.repeat_list(group_id)
        msg_number_list = history_data.msg_number_list(group_id)

    # 如无其他情况，并输出排行榜
    display_number = 10000
    minimal_msg_number = 0
    display_total_number = True

    ranking = Ranking(
        group_id, display_number, minimal_msg_number, display_total_number,
        repeat_list, msg_number_list
    )
    ranking_str = await ranking.ranking()

    if ranking_str:
        if day:
            str_data = f'{date.year} 年 {date.month} 月 {day} 日数据\n'
        else:
            str_data = f'{date.year} 年 {date.month} 月数据\n'
        str_data += ranking_str

    if not str_data:
        str_data = '找不到满足条件的数据 ~>_<~'

    return str_data

def is_valid_date(year, month, day, now):
    """ 确认输入日期是否合法
    """
    if not year and year != 0:
        return False, '请输入年份！'

    if not month:
        return False, '请输入月份，只有年份我也不知道查什么呀！'

    if month and year:
        if year < 1 or year > 9999:
            return False, '请输入 1 到 9999 的年份，超过了我就不能查惹！'
        if month > 12:
            return False, '众所周知，一年只有 12 个月！'
        if year > now.year or (year == now.year and month > now.month):
            return False, '抱歉，小誓约不能穿越时空呢！'

    if day:
        valid_day = monthrange(year, month)[1]
        if day > valid_day:
            return False, f'哼，别以为我不知道 {year} 年 {month} 月只有 {valid_day} 天！'
        if year == now.year and month == now.month and day > now.day:
            return False, '抱歉，小誓约不能穿越时空呢！'

    return True, ''
