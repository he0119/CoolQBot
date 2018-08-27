'''配置文件，不同平台设置不同'''
import logging
import os
import platform

if platform.system() == 'Linux':
    LOG_FILE_PATH = '/home/user/coolq/coolqbot.log'
    RECORDER_FILE_PATH = '/home/user/coolq/recorder.pkl'
else:
    LOG_FILE_PATH = 'coolqbot.log'
    RECORDER_FILE_PATH = 'recorder.pkl'

PLUGINS_PATH = os.path.join(os.path.abspath(
    os.path.dirname(os.path.dirname(__file__))), 'plugins')

GROUP_ID = 438789224

IS_COOLQ_PRO = bool(os.getenv('IS_COOLQ_PRO'))

def init_logger(logger):
    logger.setLevel(logging.INFO)

    # create file handler and set level to debug
    fh = logging.FileHandler(LOG_FILE_PATH)
    fh.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(filename)s - %(lineno)s - %(levelname)s - %(message)s')

    # add formatter to handler
    fh.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(fh)
