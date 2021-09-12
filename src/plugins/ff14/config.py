""" 配置文件
"""
from typing import List

from nonebot import get_driver
from pydantic import BaseSettings, validator

from src.utils.helpers import strtobool
from src.utils.plugin import PluginData

DATA = PluginData("ff14")


class Config(BaseSettings):
    # FFLogs 相关配置
    fflogs_token: str = DATA.config.get("fflogs", "token")
    # 默认从两周的数据中计算排名百分比
    fflogs_range: int = int(DATA.config.get("fflogs", "range", "14"))
    # 是否开启定时缓存
    fflogs_cache: bool = strtobool(DATA.config.get("fflogs", "cache_enable", "0"))
    # 缓存的时间
    fflogs_cache_hour: int = int(DATA.config.get("fflogs", "cache_hour", fallback="4"))
    fflogs_cache_minute: int = int(
        DATA.config.get("fflogs", "cache_minute", fallback="30")
    )
    fflogs_cache_second: int = int(
        DATA.config.get("fflogs", "cache_second", fallback="0")
    )
    # 需要缓存的副本
    fflogs_cache_boss: List[str] = DATA.config.get("fflogs", "cache_boss").split()

    @validator("fflogs_token", always=True)
    def fflogs_token_validator(cls, v):
        """验证并保存配置"""
        DATA.config.set("fflogs", "token", v)
        return v

    @validator("fflogs_cache", always=True)
    def fflogs_cache_validator(cls, v):
        """验证并保存配置"""
        if v:
            DATA.config.set("fflogs", "cache_enable", "1")
        else:
            DATA.config.set("fflogs", "cache_enable", "0")
        return v

    class Config:
        extra = "ignore"
        validate_assignment = True


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
