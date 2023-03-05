""" 配置文件
"""
from nonebot import get_driver
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    # 复读概率
    repeat_rate: int = 10
    # 复读间隔
    repeat_interval: int = 1


global_config = get_driver().config
plugin_config = Config.parse_obj(global_config)
