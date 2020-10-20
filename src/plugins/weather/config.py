from nonebot import get_driver
from pydantic import BaseSettings

from src.utils.plugin import PluginData

DATA = PluginData('weather', config=True)


class Config(BaseSettings):
    heweather_key: str = DATA.get_config('heweather', 'key')

    class Config:
        extra = "allow"


config = Config(**get_driver().config.dict())
