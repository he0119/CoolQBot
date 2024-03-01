"""打卡插件"""

from nonebot import require

require("nonebot_plugin_user")
from pathlib import Path

import nonebot
from nonebot import CommandGroup, get_driver
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from . import migrations

__plugin_meta__ = PluginMetadata(
    name="打卡",
    description="每日打卡，记录健身数据",
    usage="",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_user"),
    extra={"orm_version_location": migrations},
)

check_in = CommandGroup("check_in", block=True)

_sub_plugins = set()

global_config = get_driver().config

_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
