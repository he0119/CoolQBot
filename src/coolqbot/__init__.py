""" 机器人

需要暴露给外面的东西
"""
import os

from .bot import nonebot
from .plugin import PluginData


def restart():
    """ 重启机器人 """
    open('.COOLQBOT_RESTART', 'w').close()
    os._exit(0)
