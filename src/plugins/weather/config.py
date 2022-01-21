from nonebot import get_driver
from pydantic import BaseSettings

from src.plugins.nonebot_plugin_datastore import PluginData

DATA = PluginData("weather")


class Config(BaseSettings):
    heweather_key: str = DATA.config.get("heweather", "key")

    class Config:
        extra = "ignore"


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
