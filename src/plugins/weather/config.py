from nonebot import get_driver
from nonebot_plugin_datastore import PluginData
from pydantic import BaseSettings

DATA = PluginData("weather")


class Config(BaseSettings):
    heweather_key: str = DATA.config.get("heweather_key", "")

    class Config:
        extra = "ignore"


global_config = get_driver().config
plugin_config = Config.parse_obj(global_config)
