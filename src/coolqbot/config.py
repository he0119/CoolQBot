'''配置文件，不同平台设置不同'''
import configparser
import logging
import os
import platform
from pathlib import Path

HOME_DIR_PATH = Path(__file__).parents[1]

if platform.system() == 'Linux':
    CONFIG_PATH = Path('/home/user/coolq/bot/bot.conf')
    LOG_FILE_PATH = Path('/home/user/coolq/bot/bot.log')
    RECORDER_FILE_PATH = Path('/home/user/coolq/bot/recorder.pkl')
    HISTORY_DIR_PATH = Path('/home/user/coolq/bot/history')
    DATA_DIR_PATH = Path('/home/user/coolq/bot/data')
else:
    CONFIG_PATH = Path('bot.conf')
    LOG_FILE_PATH = Path('bot.log')
    RECORDER_FILE_PATH = Path('recorder.pkl')
    HISTORY_DIR_PATH = HOME_DIR_PATH / 'history'
    DATA_DIR_PATH = HOME_DIR_PATH / 'data'

PLUGINS_DIR_PATH = HOME_DIR_PATH / 'plugins'

# 读取配置文件
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

# 复读群号
GROUP_ID = int(config.get('bot', 'group_id'))

# 是否是酷Q专业版
IS_COOLQ_PRO = int(config.get('bot', 'is_coolq_pro'))


def init_logger(logger):
    logger.setLevel(logging.INFO)

    # create file handler and set level to debug
    fh = logging.FileHandler(LOG_FILE_PATH, encoding='UTF-8')
    fh.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(filename)s - %(lineno)s - %(levelname)s - %(message)s')

    # add formatter to handler
    fh.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(fh)
