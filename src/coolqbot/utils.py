""" 一些工具
"""
import pickle

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from coolqbot.bot import bot
from coolqbot.config import DATA_DIR_PATH
from coolqbot.plugin import PluginManager

plugin_manager = PluginManager()
scheduler = AsyncIOScheduler()


def get_history_pkl_name(dt):
    return dt.strftime('%Y-%m')


class PluginData:
    def __init__(self, name):
        self._name = name
        self._data_path = DATA_DIR_PATH / name
        self.data = {}

        self.load_pkl()

    def save_pkl(self):
        try:
            with self._data_path.open(mode='wb') as f:
                pickle.dump(self.data, f)
                bot.logger.debug(f'插件{self._name}：数据保存成功')
        except Exception as e:
            bot.logger.error(f'插件{self._name}：数据保存失败，原因是{e}')

    def load_pkl(self):
        try:
            with self._data_path.open(mode='rb') as f:
                self.data = pickle.load(f)
                bot.logger.debug(f'插件{self._name}：数据加载成功')
        except Exception as e:
            bot.logger.error(f'插件{self._name}：数据加载失败，原因是{e}')
