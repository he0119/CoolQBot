from nonebot import get_driver
from nonebot_plugin_datastore import PluginData
from pydantic import BaseSettings, validator

DATA = PluginData("morning")


class Config(BaseSettings):
    # 启动问候
    hello_group_id: list[int] = DATA.config.get("hello_group_id", [])

    @validator("hello_group_id", always=True, allow_reuse=True)
    def hello_group_id_validator(cls, v: list[int]):
        """验证并保存配置"""
        DATA.config.set("hello_group_id", v)
        return v

    # 每日早安
    morning_hour: int = DATA.config.get("morning_hour", 7)
    morning_minute: int = DATA.config.get("morning_minute", 30)
    morning_second: int = DATA.config.get("morning_second", 0)
    # 开启早安问好的群
    morning_group_id: list[int] = DATA.config.get("morning_group_id", [])

    @validator("morning_group_id", always=True, allow_reuse=True)
    def morning_group_id_validator(cls, v: list[int]):
        """验证并保存配置"""
        DATA.config.set("morning_group_id", v)
        return v

    class Config:
        extra = "ignore"
        validate_assignment = True


global_config = get_driver().config
plugin_config = Config.parse_obj(global_config)
