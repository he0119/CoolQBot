"""配置文件"""

from nonebot import get_driver, get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    repeat_rate: int = 10
    """ 复读概率 """
    repeat_interval: int = 1
    """ 复读间隔 """

    repeat_excluded_users: list[str | int] = []
    """ 排除复读的用户列表

    支持用户名或用户 ID
    """

    repeat_flush_interval: float = 2.0
    """ 缓存写入数据库的时间间隔（秒） """


global_config = get_driver().config
plugin_config = get_plugin_config(Config)
