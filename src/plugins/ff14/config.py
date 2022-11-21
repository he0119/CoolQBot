""" 配置文件
"""
from typing import List

from nonebot_plugin_datastore import PluginData
from pydantic import BaseSettings, validator

DATA = PluginData("ff14")


class Config(BaseSettings):
    # FFLogs 相关配置
    fflogs_token: str = DATA.config.get("fflogs_token", "")
    # 默认从两周的数据中计算排名百分比
    fflogs_range: int = DATA.config.get("fflogs_range", 14)
    # 是否开启定时缓存
    fflogs_enable_cache: bool = DATA.config.get("fflogs_enable_cache", False)
    # 缓存的时间
    fflogs_cache_hour: int = DATA.config.get("fflogs_cache_hour", 4)
    fflogs_cache_minute: int = DATA.config.get("fflogs_cache_minute", 30)
    fflogs_cache_second: int = DATA.config.get("fflogs_cache_second", 0)
    # 需要缓存的副本
    fflogs_cache_boss: list[str] = DATA.config.get("fflogs_cache_boss", [])

    @validator("fflogs_token", always=True, allow_reuse=True)
    def fflogs_token_validator(cls, v):
        """验证并保存配置"""
        DATA.config.set("fflogs_token", v)
        return v

    @validator("fflogs_enable_cache", always=True, allow_reuse=True)
    def fflogs_enable_cache_validator(cls, v):
        """验证并保存配置"""
        DATA.config.set("fflogs_enable_cache", v)
        return v

    @validator("fflogs_cache_boss", always=True, allow_reuse=True)
    def fflogs_cache_boss_validator(cls, v):
        """验证并保存配置"""
        DATA.config.set("fflogs_cache_boss", v)
        return v

    class Config:
        extra = "ignore"
        validate_assignment = True
