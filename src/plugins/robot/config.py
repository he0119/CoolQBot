""" 配置文件
"""
from nonebot import get_driver
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    tencent_ai_secret_id: str | None
    tencent_ai_secret_key: str | None


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
