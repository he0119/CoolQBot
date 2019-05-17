""" 一些工具
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


def get_history_pkl_name(dt):
    time_str = dt.strftime('%Y-%m')
    return time_str
