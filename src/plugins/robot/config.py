""" 配置文件
"""
from nonebot import get_driver
from pydantic import BaseSettings

from src.utils.plugin import PluginData

DATA = PluginData('robot', config=True)


class Config(BaseSettings):
    tencent_ai_app_id: str = DATA.get_config('tencent', 'app_id')
    tencent_ai_app_key: str = DATA.get_config('tencent', 'app_key')
    tuling_api_key: str = DATA.get_config('tuling', 'api_key')

    class Config:
        extra = 'ignore'


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
