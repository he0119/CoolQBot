""" 历史记录插件
"""
import re
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from coolqbot.bot import bot
from coolqbot.plugin import PluginData
from coolqbot.utils import get_history_pkl_name, scheduler
from plugins.rank import get_repeat_number_ranking, get_repeat_rate_ranking
from plugins.recorder import Recorder, recorder

DATA = PluginData('history')


@scheduler.scheduled_job('cron',
                         day=1,
                         hour=0,
                         minute=0,
                         second=0,
                         id='clear_data')
async def clear_data():
    """ 每个月最后24点(下月0点)保存记录于历史记录文件夹，并重置记录
    """
    # 保存数据到历史文件夹
    date = datetime.now() - timedelta(hours=1)
    DATA.save_pkl(recorder.get_data(), get_history_pkl_name(date))
    # 清除现有数据
    recorder.clear_data()
    bot.logger.info('记录清除完成')


@bot.on_message('group', 'private')
async def history(context):
    match = re.match(r'^\/history(?: (\d+)\-(\d+))?$|\/history (0)$',
                     context['message'])
    if match:
        str_data = ''

        year = match.group(1)
        month = match.group(2)
        if year:
            year = int(year)
        if month:
            month = int(month)

        if not year:
            str_data = '欢迎查询历史记录\n如需查询上月数据请输入/history 0\n如需查询指定月份请输入/history year-month(如2018-01)'
            return {'reply': str_data, 'at_sender': False}

        if not month:
            if year == 0:
                date = datetime.now() - relativedelta(months=1)
            else:
                str_data = '请输入月份，只有年份我也不知道查什么呀！'
                return {'reply': str_data, 'at_sender': False}

        if month and year:
            if year < 1 or year > 9999:
                str_data = '请输入1到9999的年份，超过了我就不能查惹！'
                return {'reply': str_data, 'at_sender': False}
            if month > 12:
                str_data = '请输入正确的月份，众所周知，一年只有12个月！'
                return {'reply': str_data, 'at_sender': False}
            date = datetime(year=year, month=month, day=1)

        # 尝试读取历史数据
        history_filename = get_history_pkl_name(date)
        if not DATA.exists(f'{history_filename}.pkl'):
            str_data = f'{date.year}年{date.month}月数据不存在，请换试试吧0.0'
            return {'reply': str_data, 'at_sender': False}

        # 如无其他情况，开始获取历史记录，并输出排行榜
        history_data = DATA.load_pkl(history_filename)
        display_number = 10000
        minimal_msg_number = 0
        display_total_number = True

        repeat_list = history_data['repeat_list']
        msg_number_list = history_data['msg_number_list']

        repeat_rate_ranking = await get_repeat_rate_ranking(
            repeat_list, msg_number_list, display_number, minimal_msg_number,
            display_total_number)
        repeat_number_ranking = await get_repeat_number_ranking(
            repeat_list, msg_number_list, display_number, minimal_msg_number,
            display_total_number)

        if repeat_rate_ranking and repeat_rate_ranking:
            str_data = f'{date.year}年{date.month}月数据\n'
            str_data += repeat_rate_ranking + '\n\n' + repeat_number_ranking

        if not str_data:
            str_data = '暂时还没有满足条件的数据~>_<~'

        return {'reply': str_data, 'at_sender': False}
