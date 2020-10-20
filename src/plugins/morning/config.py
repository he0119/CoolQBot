from nonebot import get_driver
from pydantic import BaseSettings

from src.utils.plugin import PluginData

DATA = PluginData('morning', config=True)


class Config(BaseSettings):
    morning_hour: int = int(DATA.get_config('morning', 'hour', fallback='7'))
    morning_minute: int = int(
        DATA.get_config('morning', 'minute', fallback='30')
    )
    morning_second: int = int(
        DATA.get_config('morning', 'second', fallback='0')
    )

    class Config:
        extra = "allow"


config = Config(**get_driver().config.dict())
