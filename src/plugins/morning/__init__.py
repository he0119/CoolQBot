""" 每日早安插件
"""
from pathlib import Path

import nonebot
from nonebot import get_driver
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="问好", description="早上好下午好晚上好", usage="", supported_adapters={"~onebot.v11"}
)

_sub_plugins = set()

global_config = get_driver().config
plugin_config = Config.parse_obj(global_config)

_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
