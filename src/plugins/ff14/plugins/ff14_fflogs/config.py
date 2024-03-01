""" 配置文件
"""
from datetime import time

from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    # FFLogs 相关配置
    # 默认从两周的数据中计算排名百分比
    fflogs_range: int = 14
    # 缓存的时间
    fflogs_cache_time: time = time(hour=4, minute=30)
    fflogs_token: str | None = None
    """FFLogs API Token"""


plugin_config = get_plugin_config(Config)
