""" 配置文件
"""
from nonebot import get_driver, get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    repeat_rate: int = 10
    """ 复读概率 """
    repeat_interval: int = 1
    """ 复读间隔 """

    repeat_migration_group_id: int | None = None
    """ 旧数据迁移的群号 """


global_config = get_driver().config
plugin_config = get_plugin_config(Config)
