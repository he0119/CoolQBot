from apscheduler.schedulers.asyncio import AsyncIOScheduler

from coolqbot.plugin import PluginManager

plugin_manager = PluginManager()
scheduler = AsyncIOScheduler()
