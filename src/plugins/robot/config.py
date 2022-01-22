""" 配置文件
"""
from nonebot import get_driver
from pydantic import BaseSettings

from nonebot_plugin_datastore import PluginData

DATA = PluginData("robot")


class Config(BaseSettings):
    tencent_ai_secret_id: str = DATA.config.get("tencent", "secret_id")
    tencent_ai_secret_key: str = DATA.config.get("tencent", "secret_key")

    class Config:
        extra = "ignore"


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
