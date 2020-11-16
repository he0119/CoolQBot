""" 配置文件
"""
from typing import List

import nonebot
from pydantic import BaseSettings, validator

from src.utils.plugin import PluginData

DATA = PluginData('repeat', config=True)


class Config(BaseSettings):
    # 复读概率
    repeat_rate: int = int(DATA.get_config('repeat', 'rate', fallback='10'))
    # 复读间隔
    repeat_interval: int = int(
        DATA.get_config('repeat', 'interval', fallback='1')
    )
    # 启用的群
    group_id: List[int] = list(
        map(int,
            DATA.get_config('repeat', 'group_id').split(','))
    ) if DATA.get_config('repeat', 'group_id') else []

    @validator('group_id', always=True)
    def group_id_validator(cls, v):
        """ 验证并保存配置 """
        DATA.set_config('repeat', 'group_id', ','.join(map(str, v)))
        return v

    class Config:
        extra = "ignore"
        validate_assignment = True


global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())
