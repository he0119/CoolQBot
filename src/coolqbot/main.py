import argparse
import asyncio
import logging

from coolqbot.bot import bot
from coolqbot.config import init_logger
from coolqbot.utils import plugin_manager, scheduler


def main(debug=False):
    init_logger(bot.logger)
    if debug:
        bot.logger.setLevel(logging.DEBUG)
    bot.logger.info('Initializing...')
    plugin_manager.load_plugin()
    scheduler.start()
    bot.run(host='127.0.0.1', port=8080, loop=asyncio.get_event_loop())


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--debug',
        action='store_true',
        default=False,
        help='Switch to DEBUG mode for better view of message.'
    )
    args = parser.parse_args()
    main(**vars(args))


if __name__ == '__main__':
    run()
