"""打卡插件"""

from pathlib import Path

import nonebot
from nonebot import get_driver, require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_orm")
require("nonebot_plugin_user")
require("src.utils.group_bind")
require("nonebot_plugin_alconna")

__plugin_meta__ = PluginMetadata(
    name="打卡",
    description="每日打卡，记录健身数据",
    usage="",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_user", "nonebot_plugin_alconna"),
)

_sub_plugins = set()

global_config = get_driver().config

_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
