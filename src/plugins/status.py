'''运行状态插件'''
import re

from coolqbot.bot import bot
from coolqbot.recorder import recorder


@bot.on_message('group', 'private')
async def status(context):
    match = re.match(r'^\/(status|状态)', context['message'])
    if match:
        str_data = f'近十分钟群内聊天数量是{recorder.message_number(10)}'
        return {'reply': str_data}
