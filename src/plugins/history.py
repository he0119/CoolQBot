'''历史记录插件'''
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from coolqbot.bot import bot
from coolqbot.recorder import Recorder
from coolqbot.config import HISTORY_DIR_PATH
from plugins.rank import get_repeat_rate_ranking, get_repeat_number_ranking

@bot.on_message('group', 'private')
async def history(context):
    match = re.match(r'^\/history', context['message'])
    if match:
        date = datetime.now() - relativedelta(months=1)
        history_file = HISTORY_DIR_PATH / f'{date.strftime("%Y-%m")}.pkl'
        bot.logger.debug(history_file)

        history_data = Recorder()
        history_data.load_data(history_file)

        display_number = 10000
        minimal_msg_number = 0
        display_total_number = True

        repeat_list = history_data.repeat_list
        msg_number_list = history_data.msg_number_list

        str_data = ''
        repeat_rate_ranking = await get_repeat_rate_ranking(repeat_list, msg_number_list, display_number, minimal_msg_number, display_total_number)
        repeat_number_ranking = await get_repeat_number_ranking(repeat_list, display_number)

        if repeat_rate_ranking and repeat_rate_ranking:
            str_data = date.strftime("%Y-%m") + '数据\n'
            str_data += repeat_rate_ranking + '\n\n' + repeat_number_ranking

        if not str_data:
            str_data = '暂时还没有满足条件的数据~>_<~'

        return {'reply': str_data, 'at_sender': False}
