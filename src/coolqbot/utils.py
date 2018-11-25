from apscheduler.schedulers.asyncio import AsyncIOScheduler

from coolqbot.plugin import PluginManager

plugin_manager = PluginManager()
scheduler = AsyncIOScheduler()

def get_history_pkl_name(dt):
    return dt.strftime('%Y-%m')
