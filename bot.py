#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

import nonebot

# You can pass some keyword args config to init function
nonebot.init()
app = nonebot.get_asgi()

# Modify some config / config depends on loaded configs
config = nonebot.get_driver().config
config.home_dir_path = Path().resolve()
# 插件数据目录
config.data_dir_path = config.home_dir_path / 'data'

# Custom your logger
from nonebot.log import default_format, logger

logger.add(
    config.data_dir_path / 'logs' / 'error.log',
    rotation='00:00',
    diagnose=False,
    level='ERROR',
    format=default_format
)

nonebot.load_plugins('src/plugins')

# 测试框架
try:
    import nonebot_test
    nonebot_test.init()
except:
    pass

if __name__ == '__main__':
    nonebot.run(app='bot:app')
