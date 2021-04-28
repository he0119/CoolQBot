from typing import List

from nonebot import get_driver
from pydantic import BaseSettings, validator

from src.utils.helpers import groupidtostr, strtogroupid
from src.utils.plugin import PluginData

DATA = PluginData('morning', config=True)


class Config(BaseSettings):
    morning_hour: int = int(DATA.get_config('morning', 'hour', fallback='7'))
    morning_minute: int = int(
        DATA.get_config('morning', 'minute', fallback='30'))
    morning_second: int = int(
        DATA.get_config('morning', 'second', fallback='0'))

    # 启用早安问好的群
    group_id: List[int] = strtogroupid(DATA.get_config('morning', 'group_id'))

    @validator('group_id', always=True)
    def group_id_validator(cls, v: List[int]):
        """ 验证并保存配置 """
        DATA.set_config('morning', 'group_id', groupidtostr(v))
        return v

    class Config:
        extra = 'ignore'
        validate_assignment = True


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
