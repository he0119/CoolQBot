""" 插件管理

这个插件默认总是启用的
"""
import re

from coolqbot import bot


@bot.on_message('group', 'private')
async def plugin(context):
    match = re.match(r'^\/plugins(?: (\w+)(?: (.+))?)?$', context['message'])
    if match:
        command = match.group(1)
        name = match.group(2)

        if command == 'enable':
            bot.plugin_manager.enable(name)
            return {'reply': f'插件 {name} 已启用'}
        if command == 'disable':
            bot.plugin_manager.disable(name)
            return {'reply': f'插件 {name} 已禁用'}
        if command == 'reload':
            bot.plugin_manager.reload(name)
            return {'reply': f'插件 {name} 已重载'}
        if command == 'status':
            return {
                'reply': f'插件  {name} 的状态：\n{bot.plugin_manager.status(name)}'
            }
        if command == 'list':
            return {'reply': str(bot.plugin_manager._plugin_list)}
        return {'reply': '抱歉，插件管理只支持 enable|disable|reload|status|list'}
