import warnings

import nonebot
from pydantic import BaseSettings


class PlugConfig(BaseSettings):

    bison_config_path: str = ""
    bison_use_pic: bool = False
    bison_init_filter: bool = True
    bison_use_queue: bool = True

    class Config:
        extra = "ignore"


global_config = nonebot.get_driver().config
plugin_config = PlugConfig(**global_config.dict())
