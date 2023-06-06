""" 打卡插件
"""
from pathlib import Path

import nonebot
from nonebot import CommandGroup, get_driver
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="打卡",
    description="每日打卡，记录健身数据",
    usage="",
    supported_adapters={"~onebot.v11", "~onebot.v12"},
)

check_in = CommandGroup("check_in", block=True)

_sub_plugins = set()

global_config = get_driver().config

_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
