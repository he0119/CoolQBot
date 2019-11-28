""" 配置文件，不同平台设置不同
"""
import configparser
import platform
import shutil
from pathlib import Path

from nonebot.default_config import *

HOME_DIR = Path(__file__).resolve().parents[1]
PLUGINS_DIR_PATH = HOME_DIR / 'plugins'

DATA_DIR = HOME_DIR / 'bot'
CONFIG_FILE_PATH = DATA_DIR / 'bot.ini'
LOG_FILE_PATH = DATA_DIR / 'bot.log'
DATA_DIR_PATH = DATA_DIR / 'data'

# 读取配置文件，如不存在就使用默认配置
EXAMPLE_CONFIG_FILE_PATH = HOME_DIR / 'bot.ini.example'
if not CONFIG_FILE_PATH.exists():
    shutil.copy(EXAMPLE_CONFIG_FILE_PATH, CONFIG_FILE_PATH)

config = configparser.ConfigParser()
config.read(CONFIG_FILE_PATH, encoding='UTF-8')

HOST = config.get('bot', 'host', fallback='127.0.0.1')
PORT = config.get('bot', 'port', fallback=8080)

SUPERUSERS = set(map(int, config['bot']['admin'].split()))
NICKNAME = config['bot']['nickname'].split()
SHORT_MESSAGE_MAX_LENGTH = 28
COMMAND_START = {'/'}

GROUP_ID = list(map(int, config['bot']['group_id'].split()))
IS_COOLQ_PRO = config.getboolean('bot', 'is_coolq_pro')
TULING_API_KEY = config.get('bot', 'tuling_api_key', fallback='')
TENCENT_AI_APP_ID = config.getint('bot', 'tencent_ai_app_id', fallback='')
TENCENT_AI_APP_KEY = config.get('bot', 'tencent_ai_app_key', fallback='')
