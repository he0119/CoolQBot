""" 机器人框架


"""
import argparse
import logging

from .bot import bot
from .logger import init_logger
from .plugin import MessageType, Plugin, plugin_manager
from .utils import scheduler


def run():
    if bot.config['CONFIG_FILE_PATH'].exists():
        bot.config.from_file(bot.config['CONFIG_FILE_PATH'])

    init_logger(bot)
    bot.logger.debug('Initializing...')

    plugin_manager.load_plugin()
    plugin_manager.enable_all()
    scheduler.start()

    bot.run(host='127.0.0.1', port=8080)
