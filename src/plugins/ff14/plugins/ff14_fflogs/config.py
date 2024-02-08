""" 配置文件
"""
from datetime import time

from pydantic import BaseModel, Extra

from src.plugins.ff14 import global_config


class Config(BaseModel, extra=Extra.ignore):
    # FFLogs 相关配置
    # 默认从两周的数据中计算排名百分比
    fflogs_range: int = 14
    # 缓存的时间
    fflogs_cache_time: time = time(hour=4, minute=30)
    fflogs_token: str | None = None
    """FFLogs API Token"""


plugin_config = Config.parse_obj(global_config)
