'''配置文件，不同平台设置不同'''
import logging
import os
import platform
from pathlib import Path

if platform.system() == 'Linux':
    LOG_FILE_PATH = Path('/home/user/coolq/coolqbot.log')
    RECORDER_FILE_PATH = Path('/home/user/coolq/recorder.pkl')
    HISTORY_DIR_PATH = Path('/home/user/coolq/history')
else:
    LOG_FILE_PATH = Path('coolqbot.log')
    RECORDER_FILE_PATH = Path('recorder.pkl')
    HISTORY_DIR_PATH = Path(__file__).parents[1] / 'history'

PLUGINS_DIR_PATH = Path(__file__).parents[1] / 'plugins'

GROUP_ID = []
GROUP_ID.append(438789224)#圆神群
GROUP_ID.append(852435740)#测试群

IS_COOLQ_PRO = bool(os.getenv('IS_COOLQ_PRO'))


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
