""" 配置文件
"""
from nonebot import get_driver
from nonebot_plugin_datastore import PluginData

DATA = PluginData("genshin")


def get_cookie(user_id: int) -> str:
    """获取用户的 cookie"""
    return DATA.config.get(f"cookie-{user_id}", "")


def set_cookie(user_id: int, cookie: str) -> None:
    """设置用户的 cookie"""
    DATA.config.set(f"cookie-{user_id}", cookie)


global_config = get_driver().config
