""" Logger 配置
"""
import logging


def add_file_handler(logger, path):
    # create file handler and set level to debug
    fh = logging.FileHandler(path, encoding='UTF-8')
    fh.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(filename)s - %(lineno)s - %(levelname)s - %(message)s'
    )

    # add formatter to handler
    fh.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(fh)
