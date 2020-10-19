""" 配置文件
"""
from typing import List

from nonebot import get_driver
from pydantic import BaseSettings, validator

from src.utils.plugin import PluginData

DATA = PluginData('ff14', config=True)


class Config(BaseSettings):
    # 新闻推送相关配置
    # 是否自动推送新闻
    push_news: bool = bool(int(DATA.get_config('ff14', 'push_news', '0')))
    # 自动推送新闻的间隔，单位 分钟
    push_news_interval: int = int(
        DATA.get_config('ff14', 'push_news_interval', '30')
    )
    # 上次推送新闻的发布 ID
    push_news_last_news_id: int = int(
        DATA.get_config('ff14', 'push_news_last_news_id', '0')
    )

    @validator('push_news', always=True)
    def push_news_validator(cls, v):
        """ 验证并保存配置 """
        if v:
            DATA.set_config('ff14', 'push_news', '1')
            return True
        DATA.set_config('ff14', 'push_news', '0')
        return False

    @validator('push_news_last_news_id', always=True)
    def push_news_last_news_id_validator(cls, v):
        """ 验证并保存配置 """
        DATA.set_config('ff14', 'push_news_last_news_id', str(v))
        return v

    # FFLogs 相关配置
    fflogs_token: str = DATA.get_config('fflogs', 'token')
    # 默认从两周的数据中计算排名百分比
    fflogs_range: int = int(DATA.get_config('fflogs', 'range', '14'))
    # 是否开启自动缓存
    fflogs_cache: bool = bool(
        int(DATA.get_config('fflogs', 'cache_enable', '0'))
    )
    # 缓存的时间
    fflogs_cache_hour: int = int(
        DATA.get_config('fflogs', 'cache_hour', fallback='4')
    )
    fflogs_cache_minute: int = int(
        DATA.get_config('fflogs', 'cache_minute', fallback='30')
    )
    fflogs_cache_second: int = int(
        DATA.get_config('fflogs', 'cache_second', fallback='0')
    )
    # 缓存的副本
    fflogs_cache_boss: List[str] = DATA.get_config(
        'fflogs', 'fflogs_cache_boss'
    ).split()

    @validator('fflogs_token', always=True)
    def fflogs_token_validator(cls, v):
        """ 验证并保存配置 """
        DATA.set_config('fflogs', 'token', v)
        return v

    class Config:
        extra = 'ignore'
        validate_assignment = True


config = Config(**get_driver().config.dict())
