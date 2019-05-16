""" 插件管理

这个插件是默认启用的
"""
import re

from coolqbot.bot import bot
from coolqbot.utils import plugin_manager


@bot.on_message('group', 'private')
async def plugins(context):
    match = re.match(r'^\/plugins(?: (\w+)(?: (.+))?)?$', context['message'])
    if match:
        command = match.group(1)
        name = match.group(2)

        str_data = ''
        if command == 'enable':
            plugin_manager.enable(name)
            str_data = '启用插件 {name}'
        elif command == 'disable':
            plugin_manager.disable(name)
            str_data = '停止插件 {name}'
        elif command == 'reload':
            plugin_manager.reload(name)
            str_data = '重载插件 {name}'
        elif command == 'status':
            str_data += f'插件  {name} 的状态：\n{plugin_manager.status(name)}'
        elif command == 'list':
            str_data += str(plugin_manager._plugin_list)
        else:
            str_data += '抱歉，插件管理只支持 enable|disable|reload|status|list'

        return {'reply': str_data}
