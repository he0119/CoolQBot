""" 配置文件，不同平台设置不同
"""
import configparser
import platform
from pathlib import Path

from nonebot.default_config import *

# 根据运行的系统，配置不同的设置
if platform.system() == 'Linux':
    HOME_DIR = Path('/home/user/coolq/bot')
    PLUGINS_DIR_PATH = Path('/home/user/coolqbot/plugins')
else:
    HOME_DIR = Path(__file__).resolve().parents[1] / 'bot'
    PLUGINS_DIR_PATH = HOME_DIR.parent / 'plugins'

CONFIG_FILE_PATH = HOME_DIR / 'bot.ini'
LOG_FILE_PATH = HOME_DIR / 'bot.log'
DATA_DIR_PATH = HOME_DIR / 'data'

# 读取配置文件
config = configparser.ConfigParser()
config.read(CONFIG_FILE_PATH, encoding='UTF-8')

SUPERUSERS = config['bot']['admin'].split(',')
NICKNAME = config['bot']['nickname'].split(',')
