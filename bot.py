#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import nonebot

# Custom your logger
#
from nonebot.log import logger, default_format
logger.add(
    "error.log",
    rotation="00:00",
    diagnose=False,
    level="ERROR",
    format=default_format
)

# You can pass some keyword args config to init function
nonebot.init()
app = nonebot.get_asgi()

# Modify some config / config depends on loaded configs
#
config = nonebot.get_driver().config
config.home_dir_path = Path().resolve()
# 插件数据目录
config.data_dir_path = config.home_dir_path / 'data'

nonebot.load_plugins("src/plugins")

if __name__ == "__main__":
    nonebot.run(app="bot:app")
