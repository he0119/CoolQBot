""" 历史记录
"""
from calendar import monthrange
from datetime import datetime
from typing import Tuple

from nonebot.adapters.onebot.v11 import Bot

from ... import DATA, Recorder, plugin_config, recorder_obj
from ..rank.data_source import Ranking


async def get_history(bot: Bot, year: int, month: int, day: int, group_id: int) -> str:
    """获取历史数据"""
    if group_id not in plugin_config.group_id:
        return "该群未开启复读功能，无法获取历史排行榜。"

    str_data = ""
    now = datetime.now()
    is_valid, message = is_valid_date(year, month, day, now)
    if not is_valid:
        return message
    date = datetime(year=year, month=month, day=1)

    # 尝试读取历史数据
    # 如果是本月就直接从 recorder 中获取数据
    # 不是则从历史记录中获取
    if year == now.year and month == now.month:
        history_data = recorder_obj
    else:
        history_filename = Recorder.get_history_pkl_name(date)
        if not DATA.exists(history_filename):
            if day:
                str_data = f"{date.year} 年 {date.month} 月 {day} 日的数据不存在，请换个试试吧 ~>_<~"
            else:
                str_data = f"{date.year} 年 {date.month} 月的数据不存在，请换个试试吧 0.0"
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
        bot,
        group_id,
        display_number,
        minimal_msg_number,
        display_total_number,
        repeat_list,
        msg_number_list,
    )
    ranking_str = await ranking.ranking()

    if ranking_str:
        if day:
            str_data = f"{date.year} 年 {date.month} 月 {day} 日数据\n"
        else:
            str_data = f"{date.year} 年 {date.month} 月数据\n"
        str_data += ranking_str

    if not str_data:
        str_data = "找不到满足条件的数据 ~>_<~"

    return str_data


def is_valid_date(year: int, month: int, day: int, now: datetime) -> tuple[bool, str]:
    """确认输入日期是否合法"""
    if not year and year != 0:
        return False, "请输入年份！"

    if not month:
        return False, "请输入月份，只有年份我也不知道查什么呀！"

    if month and year:
        if year < 1 or year > 9999:
            return False, "请输入 1 到 9999 的年份，超过了我就不能查惹！"
        if month > 12:
            return False, "众所周知，一年只有 12 个月！"
        if year > now.year or (year == now.year and month > now.month):
            return False, "抱歉，小誓约不能穿越时空呢！"

    if day:
        valid_day = monthrange(year, month)[1]
        if day > valid_day:
            return False, f"哼，别以为我不知道 {year} 年 {month} 月只有 {valid_day} 天！"
        if year == now.year and month == now.month and day > now.day:
            return False, "抱歉，小誓约不能穿越时空呢！"

    return True, ""
