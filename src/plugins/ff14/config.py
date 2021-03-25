""" 配置文件
"""
from typing import List

from nonebot import get_driver
from pydantic import BaseSettings, validator
from dateutil.parser import parse
from datetime import date, datetime

from src.utils.helpers import groupidtostr, strtobool, strtogroupid
from src.utils.plugin import PluginData

DATA = PluginData('ff14', config=True)


class Config(BaseSettings):
    # 新闻推送相关配置
    # 自动推送新闻的间隔，单位 分钟
    push_news_interval: int = int(
        DATA.get_config('ff14', 'push_news_interval', '30'))
    # 上次推送新闻的发布时间
    push_news_last_news_date: datetime = parse(
        DATA.get_config('ff14', 'push_news_last_news_date', '2000-01-01'))

    # 启用新闻推送的群
    push_news_group_id: List[int] = strtogroupid(
        DATA.get_config('ff14', 'push_news_group_id'))

    @validator('push_news_last_news_date', always=True)
    def push_news_last_news_date_validator(cls, v: datetime):
        """ 验证并保存配置 """
        DATA.set_config('ff14', 'push_news_last_news_date', v.isoformat())
        return v

    @validator('push_news_group_id', always=True)
    def push_news_group_id_validator(cls, v: List[int]):
        """ 验证并保存配置 """
        DATA.set_config('ff14', 'push_news_group_id', groupidtostr(v))
        return v

    # FFLogs 相关配置
    fflogs_token: str = DATA.get_config('fflogs', 'token')
    # 默认从两周的数据中计算排名百分比
    fflogs_range: int = int(DATA.get_config('fflogs', 'range', '14'))
    # 是否开启定时缓存
    fflogs_cache: bool = strtobool(
        DATA.get_config('fflogs', 'cache_enable', '0'))
    # 缓存的时间
    fflogs_cache_hour: int = int(
        DATA.get_config('fflogs', 'cache_hour', fallback='4'))
    fflogs_cache_minute: int = int(
        DATA.get_config('fflogs', 'cache_minute', fallback='30'))
    fflogs_cache_second: int = int(
        DATA.get_config('fflogs', 'cache_second', fallback='0'))
    # 需要缓存的副本
    fflogs_cache_boss: List[str] = DATA.get_config('fflogs',
                                                   'cache_boss').split()

    @validator('fflogs_token', always=True)
    def fflogs_token_validator(cls, v):
        """ 验证并保存配置 """
        DATA.set_config('fflogs', 'token', v)
        return v

    @validator('fflogs_cache', always=True)
    def fflogs_cache_validator(cls, v):
        """ 验证并保存配置 """
        if v:
            DATA.set_config('fflogs', 'cache_enable', '1')
        else:
            DATA.set_config('fflogs', 'cache_enable', '0')
        return v

    class Config:
        extra = 'ignore'
        validate_assignment = True


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
