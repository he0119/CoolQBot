""" 配置文件
"""
from datetime import time

from pydantic import BaseSettings

from ... import global_config


class Config(BaseSettings):
    # FFLogs 相关配置
    # 默认从两周的数据中计算排名百分比
    fflogs_range: int = 14
    # 缓存的时间
    fflogs_cache_time: time = time(hour=4, minute=30)

    class Config:
        extra = "ignore"


plugin_config = Config.parse_obj(global_config)
