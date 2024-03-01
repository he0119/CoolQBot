"""roll 点插件

NGA 风格 ROLL 点
掷骰子
"""

from pathlib import Path

import nonebot
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="Roll",
    description="Roll 点与掷骰子",
    usage="",
)

_sub_plugins = set()
_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
