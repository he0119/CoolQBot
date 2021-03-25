""" 配置文件
"""
from typing import List

from nonebot import get_driver
from pydantic import BaseSettings, validator

from src.utils.helpers import groupidtostr, strtogroupid
from src.utils.plugin import PluginData

DATA = PluginData('pcr', config=True)


class Config(BaseSettings):
    # 新闻推送相关配置
    # 自动推送新闻的间隔，单位 分钟
    push_news_interval: int = int(
        DATA.get_config('news', 'push_news_interval', '30'))
    # 上次推送新闻的发布 ID
    push_news_last_news_id: int = int(
        DATA.get_config('news', 'push_news_last_news_id', '0'))

    @validator('push_news_last_news_id')
    def push_news_last_news_id_validator(cls, v):
        """ 验证并保存配置 """
        DATA.set_config('news', 'push_news_last_news_id', str(v))
        return v

    # 启用新闻推送的群
    push_news_group_id: List[int] = strtogroupid(
        DATA.get_config('news', 'group_id'))

    @validator('push_news_group_id', always=True)
    def push_news_group_id_validator(cls, v: List[int]):
        """ 验证并保存配置 """
        DATA.set_config('news', 'group_id', groupidtostr(v))
        return v

    # 日程推送功能
    calender_hour: int = int(DATA.get_config('calender', 'hour', fallback='7'))
    calender_minute: int = int(
        DATA.get_config('calender', 'minute', fallback='30'))
    calender_second: int = int(
        DATA.get_config('calender', 'second', fallback='0'))

    # 启用日程推送的群
    push_calender_group_id: List[int] = strtogroupid(
        DATA.get_config('calender', 'group_id'))

    @validator('push_calender_group_id', always=True)
    def push_calender_group_id_validator(cls, v: List[int]):
        """ 验证并保存配置 """
        DATA.set_config('calender', 'group_id', groupidtostr(v))
        return v

    class Config:
        extra = 'ignore'
        validate_assignment = True


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
