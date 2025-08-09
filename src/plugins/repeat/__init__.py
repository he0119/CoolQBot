"""复读插件

按照一定条件复读聊天
拥有一些配套功能，如复读排行榜，排行榜历史记录，复读状态
"""

from pathlib import Path

import nonebot
from nonebot import get_driver, get_plugin_config, require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_datastore")
require("nonebot_plugin_orm")
require("nonebot_plugin_user")
require("nonebot_plugin_alconna")

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="复读",
    description="与复读有关的功能",
    usage="与复读有关的功能",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)

_sub_plugins = set()

global_config = get_driver().config
plugin_config = get_plugin_config(Config)

_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
