""" 配置文件
"""
from nonebot import get_driver
from pydantic import BaseSettings

from src.utils.plugin import PluginData

DATA = PluginData('repeat', config=True)


class Config(BaseSettings):
    # 复读概率
    repeat_rate: int = int(DATA.get_config('repeat', 'rate', fallback='10'))
    # 复读间隔
    repeat_interval: int = int(
        DATA.get_config('repeat', 'interval', fallback='1')
    )

    class Config:
        extra = "allow"


config = Config(**get_driver().config.dict())
