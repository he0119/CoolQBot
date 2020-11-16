from nonebot import get_driver
from pydantic import BaseSettings

from src.utils.plugin import PluginData

DATA = PluginData('weather', config=True)


class Config(BaseSettings):
    heweather_key: str = DATA.get_config('heweather', 'key')

    class Config:
        extra = 'ignore'


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
