""" 一些工具
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from coolqbot.plugin import PluginManager

plugin_manager = PluginManager()
scheduler = AsyncIOScheduler()


def get_history_pkl_name(dt):
    time_str = dt.strftime('%Y-%m')
    return f'{time_str}.pkl'
