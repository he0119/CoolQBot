'''运行状态插件'''
import re

from coolqbot.bot import bot
from coolqbot.recorder import recorder


@bot.on_message('group', 'private')
async def status(context):
    match = re.match(r'^\/(status|状态)', context['message'])
    if match:
        str_data = f'近十分钟群内聊天数量是{recorder.message_number(10)}条'
        repeat_num = get_total_number(recorder.repeat_list)
        msg_num = get_total_number(recorder.msg_number_list)
        repeat_rate = repeat_num / msg_num
        str_data += f'\n现在的群内聊天总数是{msg_num}条'
        str_data += f'\n复读概率是{repeat_rate*100:.2f}%'
        return {'reply': str_data, 'at_sender': False}


def get_total_number(record_list):
    num = 0
    for dummy, v in record_list.items():
        num += v
    return num
