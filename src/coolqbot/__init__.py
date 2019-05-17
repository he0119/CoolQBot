import argparse
import logging

from .bot import bot
from .config import init_logger
from .plugin import MessageType, Plugin, plugin_manager
from .utils import scheduler


def main(debug=False):
    init_logger(bot.logger)
    if debug:
        bot.logger.setLevel(logging.DEBUG)
    bot.logger.debug('Initializing...')

    plugin_manager.load_plugin()
    plugin_manager.enable_all()
    scheduler.start()

    bot.run(host='127.0.0.1', port=8080)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--debug',
        action='store_true',
        default=False,
        help='Switch to DEBUG mode for better view of message.')
    args = parser.parse_args()
    main(**vars(args))
