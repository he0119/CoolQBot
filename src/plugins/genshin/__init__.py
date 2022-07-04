""" 原神 """
from pathlib import Path

import nonebot
from nonebot import CommandGroup
from nonebot.plugin import PluginMetadata

from .api import Genshin
from .config import get_cookie, set_cookie

__plugin_meta__ = PluginMetadata(
    name="原神",
    description="与原神有关的功能",
    usage="与原神有关的功能",
)


_sub_plugins = set()

genshin = CommandGroup("ys")

_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
