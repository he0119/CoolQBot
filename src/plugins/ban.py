""" 自主禁言插件
"""
import re

from coolqbot import MessageType, bot


class Ban(bot.Plugin):
    async def on_message(self, context):
        match = re.match(r'^\/ban(?: (\d*))?$', context['message'])
        if match:
            args = match.group(1)

            if args:
                duration = int(args) * 60
            else:
                # 默认10分钟
                duration = 10 * 60

            await bot.set_group_ban(group_id=bot.config['GROUP_ID'],
                                    user_id=context['user_id'],
                                    duration=duration)


bot.plugin_manager.register(Ban(bot, MessageType.Group, MessageType.Private))
