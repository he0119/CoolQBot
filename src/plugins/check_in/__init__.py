""" 打卡插件
"""
from nonebot import require

require("src.plugins.user")
from pathlib import Path

import nonebot
from nonebot import CommandGroup, get_driver
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_datastore.db import pre_db_init


@pre_db_init
async def upgrade_user():
    from nonebot_plugin_datastore.script.command import upgrade
    from nonebot_plugin_datastore.script.utils import Config

    config = Config("user")
    await upgrade(config, "head")


__plugin_meta__ = PluginMetadata(
    name="打卡",
    description="每日打卡，记录健身数据",
    usage="",
    supported_adapters=inherit_supported_adapters("user"),
)

check_in = CommandGroup("check_in", block=True)

_sub_plugins = set()

global_config = get_driver().config

_sub_plugins |= nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
