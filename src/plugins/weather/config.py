from nonebot import get_driver, get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    heweather_key: str | None = None


global_config = get_driver().config
plugin_config = get_plugin_config(Config)
