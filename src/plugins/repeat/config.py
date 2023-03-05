""" 配置文件
"""
from nonebot import get_driver
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    repeat_rate: int = 10
    """ 复读概率 """
    repeat_interval: int = 1
    """ 复读间隔 """

    repeat_migration_group_id: int | None = None
    """ 旧数据迁移的群号 """


global_config = get_driver().config
plugin_config = Config.parse_obj(global_config)
