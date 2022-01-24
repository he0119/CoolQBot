""" 配置文件
"""
from nonebot import get_driver
from nonebot_plugin_datastore import PluginData
from pydantic import BaseSettings, validator

DATA = PluginData("repeat")


class Config(BaseSettings):
    # 复读概率
    repeat_rate: int = DATA.config.get("repeat_rate", 10)
    # 复读间隔
    repeat_interval: int = DATA.config.get("repeat_interval", 1)
    # 启用的群
    group_id: list[int] = DATA.config.get("group_id", [])

    @validator("group_id", always=True, allow_reuse=True)
    def group_id_validator(cls, v):
        """验证并保存配置"""
        DATA.config.set("group_id", v)
        return v

    class Config:
        extra = "ignore"
        validate_assignment = True


global_config = get_driver().config
plugin_config = Config(**global_config.dict())
