'''Bot'''
from aiocqhttp import CQHttp

from coolqbot.plugin import PluginManager

bot = CQHttp(api_root='http://127.0.0.1:5700/')
plugin_manager = PluginManager()
