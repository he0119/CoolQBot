""" 运行状态插件
"""
import re
from datetime import datetime

from dateutil.relativedelta import relativedelta

from coolqbot import MessageType, bot
from plugins.recorder import recorder


class Status(bot.Plugin):
    async def on_message(self, context):
        match = re.match(r'^\/(status|状态)$', context['message'])
        if match:
            str_data = f'近十分钟群内聊天数量是 {recorder.message_number(10)} 条'

            repeat_num = get_total_number(recorder.get_repeat_list())
            msg_num = get_total_number(recorder.get_msg_number_list())
            today_msg_num = get_total_number(
                recorder.get_msg_number_list_by_day(datetime.now().day))

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
            return {'reply': str_data, 'at_sender': False}


bot.plugin_manager.register(Status(bot, MessageType.Group,
                                   MessageType.Private))


def get_total_number(record_list):
    """ 获取总数
    """
    num = 0
    for dummy, v in record_list.items():
        num += v
    return num


@bot.scheduler.scheduled_job('interval', seconds=5, id='check_status')
async def check_status():
    """ 检测是否需要发送问好信息
    """
    if recorder.coolq_status and not recorder.send_hello:
        hello_str = get_message()
        await bot.send_msg(message_type='group',
                           group_id=bot.config['GROUP_ID'],
                           message=hello_str)
        recorder.send_hello = True
        bot.logger.info('发送问好信息')


def get_message():
    """ 获得消息

    TODO: 每次启动时问好词根据时间不同而不同
    """

    return '早上好呀！'
