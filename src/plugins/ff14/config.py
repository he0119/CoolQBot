""" 配置文件
"""
from nonebot import get_driver
from pydantic import BaseSettings, validator

from src.utils.plugin import PluginData

DATA = PluginData('ff14', config=True)


class Config(BaseSettings):
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

    class Config:
        extra = "ignore"
        validate_assignment = True


ff14_config = Config(**get_driver().config.dict())
