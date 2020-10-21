""" 配置文件
"""
from nonebot import get_driver
from pydantic import BaseSettings, validator

from src.utils.plugin import PluginData

DATA = PluginData('pcr', config=True)


class Config(BaseSettings):
    # 新闻推送相关配置
    # 是否自动推送新闻
    push_news: bool = bool(int(DATA.get_config('news', 'push_news', '0')))
    # 自动推送新闻的间隔，单位 分钟
    push_news_interval: int = int(
        DATA.get_config('news', 'push_news_interval', '30')
    )
    # 上次推送新闻的发布 ID
    push_news_last_news_id: int = int(
        DATA.get_config('news', 'push_news_last_news_id', '0')
    )

    @validator('push_news')
    def push_news_validator(cls, v):
        """ 验证并保存配置 """
        if v:
            DATA.set_config('news', 'push_news', '1')
            return True
        DATA.set_config('news', 'push_news', '0')
        return False

    @validator('push_news_last_news_id')
    def push_news_last_news_id_validator(cls, v):
        """ 验证并保存配置 """
        DATA.set_config('news', 'push_news_last_news_id', str(v))
        return v

    push_calender: bool = bool(
        int(DATA.get_config('calender', 'push_calender', '0'))
    )
    calender_hour: int = int(DATA.get_config('calender', 'hour', fallback='7'))
    calender_minute: int = int(
        DATA.get_config('calender', 'minute', fallback='30')
    )
    calender_second: int = int(
        DATA.get_config('calender', 'second', fallback='0')
    )

    @validator('push_calender')
    def push_calender_validator(cls, v):
        """ 验证并保存配置 """
        if v:
            DATA.set_config('calender', 'push_calender', '1')
            return True
        DATA.set_config('calender', 'push_calender', '0')
        return False

    class Config:
        extra = 'allow'
        validate_assignment = True


config = Config(**get_driver().config.dict())
