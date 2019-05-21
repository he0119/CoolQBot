""" Logger 配置
"""
import logging


def init_logger(bot):
    bot.logger.setLevel(logging.INFO)
    if bot.config['DEBUG']:
        bot.logger.setLevel(logging.DEBUG)

    # create file handler and set level to debug
    fh = logging.FileHandler(bot.config['LOG_FILE_PATH'], encoding='UTF-8')
    fh.setLevel(logging.INFO)

    # create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(filename)s - %(lineno)s - %(levelname)s - %(message)s'
    )

    # add formatter to handler
    fh.setFormatter(formatter)

    # add ch to logger
    bot.logger.addHandler(fh)
