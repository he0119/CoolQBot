""" 自主禁言插件
"""
import re

from coolqbot.bot import bot
from coolqbot.config import GROUP_ID


@bot.on_message('group', 'private')
async def ban(context):
    match = re.match(r'^\/ban ?(\w*)?', context['message'])
    if match:
        args = match.group(1)

        # 默认10分钟
        duration = 10 * 60

        if args:
            duration = int(args)

        await bot.set_group_ban(group_id=GROUP_ID, user_id=context['user_id'], duration=duration)
