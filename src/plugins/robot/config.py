""" 配置文件
"""
from nonebot import get_driver
from nonebot_plugin_datastore import PluginData
from pydantic import BaseSettings

DATA = PluginData("robot")


class Config(BaseSettings):
    tencent_ai_secret_id: str = DATA.config.get("tencent_secret_id", "")
    tencent_ai_secret_key: str = DATA.config.get("tencent_secret_key", "")

    class Config:
        extra = "ignore"


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
