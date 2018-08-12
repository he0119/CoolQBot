import argparse
import logging

from coolqbot.logger import logger
from coolqbot.bot import bot, plugin_manager


def main_loop(debug=False):
    if debug:
        logger.setLevel(logging.DEBUG)
    logger.info('Initializing...')
    plugin_manager.load_plugin()

    bot.run(host='127.0.0.1', port=8080)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--debug',
        action='store_true',
        default=False,
        help='Switch to DEBUG mode for better view of message.'
    )
    args = parser.parse_args()
    main_loop(**vars(args))


if __name__ == '__main__':
    run()
