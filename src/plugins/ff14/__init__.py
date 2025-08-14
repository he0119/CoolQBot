"""最终幻想XIV"""

from pathlib import Path

import nonebot
from nonebot import get_driver, require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_datastore")
require("nonebot_plugin_orm")
require("nonebot_plugin_user")
require("src.utils.group_bind")
require("nonebot_plugin_alconna")

__plugin_meta__ = PluginMetadata(
    name="最终幻想XIV",
    description="与最终幻想XIV有关的功能",
    usage="与最终幻想XIV有关的功能",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)

global_config = get_driver().config

_sub_plugins = set()
_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
