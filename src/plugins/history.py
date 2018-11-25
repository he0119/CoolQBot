'''历史记录插件'''
import re
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from coolqbot.bot import bot
from coolqbot.config import HISTORY_DIR_PATH
from coolqbot.recorder import Recorder
from coolqbot.utils import get_history_pkl_name
from plugins.rank import get_repeat_number_ranking, get_repeat_rate_ranking


@bot.on_message('group', 'private')
async def history(context):
    match = re.match(r'^\/history ?(\d+)\-?(\d+)?|^\/history',
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
            str_data = '欢迎查询历史记录\n如需查询上月数据请输入/history 1\n如需查询指定月份请输入/history year-month(如2018-01)'
            return {'reply': str_data, 'at_sender': False}

        if year and month:
            if year < 1 or year > 9999:
                str_data = '请输入1到9999的年份，超过了我就不能查惹'
                return {'reply': str_data, 'at_sender': False}
            if month > 12:
                str_data = '请输入正确的月份，众所周知，一年只有12个月'
                return {'reply': str_data, 'at_sender': False}
            date = datetime(year=year, month=month, day=1)
        else:
            date = datetime.now() - relativedelta(months=1)

        history_file = HISTORY_DIR_PATH / f'{get_history_pkl_name(date)}.pkl'
        bot.logger.debug(history_file)

        if not history_file.exists():
            str_data = f'{date.year}年{date.month}月数据不存在，请换试试吧0.0'
            return {'reply': str_data, 'at_sender': False}

        # 如无其他情况，开始获取历史记录，并输出排行榜
        history_data = Recorder(history_file)
        display_number = 10000
        minimal_msg_number = 0
        display_total_number = True

        repeat_list = history_data.repeat_list
        msg_number_list = history_data.msg_number_list

        repeat_rate_ranking = await get_repeat_rate_ranking(repeat_list, msg_number_list, display_number, minimal_msg_number, display_total_number)
        repeat_number_ranking = await get_repeat_number_ranking(repeat_list, display_number)

        if repeat_rate_ranking and repeat_rate_ranking:
            str_data = f'{date.year}年{date.month}月数据\n'
            str_data += repeat_rate_ranking + '\n\n' + repeat_number_ranking

        if not str_data:
            str_data = '暂时还没有满足条件的数据~>_<~'

        return {'reply': str_data, 'at_sender': False}
