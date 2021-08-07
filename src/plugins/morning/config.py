from nonebot import get_driver
from pydantic import BaseSettings, validator

from src.utils.helpers import groupidtostr, strtogroupid
from src.utils.plugin import PluginData

DATA = PluginData('morning')


class Config(BaseSettings):
    morning_hour: int = DATA.config.getint('morning', 'hour', fallback=7)
    morning_minute: int = DATA.config.getint('morning', 'minute', fallback=30)
    morning_second: int = DATA.config.getint('morning', 'second', fallback=0)

    # 启用早安问好的群
    group_id: list[int] = strtogroupid(DATA.config.get('morning', 'group_id'))

    @validator('group_id', always=True)
    def group_id_validator(cls, v: list[int]):
        """ 验证并保存配置 """
        DATA.config.set('morning', 'group_id', groupidtostr(v))
        return v

    class Config:
        extra = 'ignore'
        validate_assignment = True


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
