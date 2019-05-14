""" 历史记录插件
"""
import re
from calendar import monthrange
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from coolqbot.bot import bot
from coolqbot.plugin import PluginData
from coolqbot.utils import get_history_pkl_name, scheduler
from plugins.rank import Ranking
from plugins.recorder import Recorder, recorder

DATA = PluginData('history')


@scheduler.scheduled_job('cron',
                         day=1,
                         hour=0,
                         minute=0,
                         second=0,
                         id='clear_data')
async def clear_data():
    """ 每个月最后一天 24 点（下月 0 点）保存记录于历史记录文件夹，并重置记录
    """
    # 保存数据到历史文件夹
    date = datetime.now() - timedelta(hours=1)
    DATA.save_pkl(recorder.get_data(history=True), get_history_pkl_name(date))
    # 清除现有数据
    recorder.clear_data()
    bot.logger.info('记录清除完成')


@bot.on_message('group', 'private')
async def history(context):
    match = re.match(r'^\/history(?: (\d+)(?:\-(\d+)(?:\-(\d+))?)?)?$',
                     context['message'])
    if match:
        str_data = ''
        now = datetime.now()

        year = match.group(1)
        month = match.group(2)
        day = match.group(3)

        if year:
            year = int(year)
        if month:
            month = int(month)
        if day:
            day = int(day)

        # 确认输入是否合法
        if not year and year != 0:
            str_data = '欢迎查询历史记录\n如需查询上月数据请输入/history 0\n如需查询指定月份请输入/history year-month（如 2018-01）\n如需查询指定日期请输入/history year-month-day（如 2018-01-01）'
            return {'reply': str_data, 'at_sender': False}

        if not month:
            if year == 0:
                date = datetime.now() - relativedelta(months=1)
            else:
                str_data = '请输入月份，只有年份我也不知道查什么呀！'
                return {'reply': str_data, 'at_sender': False}

        if month and year:
            if year < 1 or year > 9999:
                str_data = '请输入 1 到 9999 的年份，超过了我就不能查惹！'
                return {'reply': str_data, 'at_sender': False}
            if month > 12:
                str_data = '众所周知，一年只有 12 个月！'
                return {'reply': str_data, 'at_sender': False}
            if year > now.year or (year == now.year and month > now.month):
                str_data = '抱歉，小誓约不能穿越时空呢！'
                return {'reply': str_data, 'at_sender': False}
            date = datetime(year=year, month=month, day=1)

        if day:
            valid_day = monthrange(year, month)[1]
            if day > valid_day:
                str_data = f'哼，别以为我不知道 {year} 年 {month} 月只有 {valid_day} 天！'
                return {'reply': str_data, 'at_sender': False}
            if year == now.year and month == now.month and day > now.day:
                str_data = '抱歉，小誓约不能穿越时空呢！'
                return {'reply': str_data, 'at_sender': False}

        # 尝试读取历史数据
        # 如果是本月就直接从 recorder 中获取数据
        # 不是则从历史记录中获取
        if year == now.year and month == now.month:
            history_data = recorder
        else:
            history_filename = get_history_pkl_name(date)
            if not DATA.exists(f'{history_filename}.pkl'):
                if day:
                    str_data = f'找不到 {year} 年 {month} 月 {day} 日的数据，请换个试试吧 ~>_<~'
                else:
                    str_data = f'{year} 年 {month} 月的数据不存在，请换个试试吧 0.0'
                return {'reply': str_data, 'at_sender': False}
            data = DATA.load_pkl(history_filename)
            history_data = Recorder(data)

        if day:
            repeat_list = history_data.get_repeat_list_by_day(day)
            msg_number_list = history_data.get_msg_number_list_by_day(day)
        else:
            repeat_list = history_data.get_repeat_list()
            msg_number_list = history_data.get_msg_number_list()

        # 如无其他情况，并输出排行榜
        display_number = 10000
        minimal_msg_number = 0
        display_total_number = True

        ranking = Ranking(display_number, minimal_msg_number,
                          display_total_number, repeat_list, msg_number_list)
        ranking_str = await ranking.ranking()

        if ranking_str:
            if day:
                str_data = f'{year} 年 {month} 月 {day} 日数据\n'
            else:
                str_data = f'{year} 年 {month} 月数据\n'
            str_data += ranking_str

        if not str_data:
            str_data = '找不到满足条件的数据 ~>_<~'

        return {'reply': str_data, 'at_sender': False}
