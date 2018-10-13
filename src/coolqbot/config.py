'''配置文件，不同平台设置不同'''
import logging
import os
import platform
from pathlib import Path, PurePosixPath

if platform.system() == 'Linux':
    LOG_FILE_PATH = PurePosixPath('/home/user/coolq/coolqbot.log')
    RECORDER_FILE_PATH = PurePosixPath('/home/user/coolq/recorder.pkl')
else:
    LOG_FILE_PATH = Path('coolqbot.log')
    RECORDER_FILE_PATH = Path('recorder.pkl')

PLUGINS_PATH = Path(__file__).parents[1] / 'plugins'

GROUP_ID = 438789224

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
