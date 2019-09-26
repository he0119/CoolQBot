""" 机器人

需要暴露给外面的东西
"""
from .bot import nonebot as bot
from .plugin import PluginData

bot.load_plugins(bot.get_bot().config.PLUGINS_DIR_PATH, 'plugins')
