""" 最终幻想XIV
"""

from pathlib import Path

import nonebot
from nonebot import CommandGroup, get_driver
from nonebot.plugin import PluginMetadata

from .config import DATA, Config

__plugin_meta__ = PluginMetadata(
    name="最终幻想XIV",
    description="与最终幻想XIV有关的功能",
    usage="与最终幻想XIV有关的功能",
)

ff14 = CommandGroup("ff14", block=True)

_sub_plugins = set()

global_config = get_driver().config
plugin_config = Config.parse_obj(global_config)

_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
