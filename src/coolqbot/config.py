'''配置文件，不同平台设置不同'''
import platform
import logging

if platform.system() == 'Linux':
    LOG_FILE_PATH = '/home/user/coolq/coolqbot.log'
    RECORDER_FILE_PATH = '/home/user/coolq/recorder.pickle'
else:
    LOG_FILE_PATH = 'coolqbot.log'
    RECORDER_FILE_PATH = 'recorder.pickle'


def init_logger(logger):
    # create logger
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
