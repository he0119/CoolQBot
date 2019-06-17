""" 初始化机器人
"""
import nonebot

import coolqbot.config as config

from .logger import add_file_handler

add_file_handler(nonebot.logger, config.LOG_FILE_PATH)

nonebot.init(config)
nonebot.load_plugins(config.PLUGINS_DIR_PATH, 'plugins')
