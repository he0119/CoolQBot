""" 复读插件

按照一定条件复读聊天
拥有一些配套功能，如复读排行榜，排行榜历史记录，复读状态
"""
from pathlib import Path

import nonebot
from nonebot import CommandGroup, get_driver
from nonebot.plugin import PluginMetadata

from .config import DATA, Config

__plugin_meta__ = PluginMetadata(
    name="复读",
    description="复读相关的功能",
    usage="复读相关的功能",
)

_sub_plugins = set()

repeat = CommandGroup("repeat")
global_config = get_driver().config
plugin_config = Config.parse_obj(global_config)
from .recorder import Recorder

recorder_obj = Recorder("recorder.pkl")

_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
