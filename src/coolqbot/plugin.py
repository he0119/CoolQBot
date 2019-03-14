""" 插件相关
"""
import os
import pickle

from coolqbot.bot import bot
from coolqbot.config import DATA_DIR_PATH, PLUGINS_DIR_PATH


class PluginManager:

    def __init__(self):
        self._plugin_prefix = 'plugins'

    def _get_plugin_name(self, name):
        return f'{self._plugin_prefix}.{name}'

    def load_plugin(self):
        filenames = [x.stem for x in PLUGINS_DIR_PATH.iterdir() if x.is_file()]
        for plugin_name in filenames:
            try:
                __import__(self._get_plugin_name(plugin_name))
                bot.logger.info(f'Plugin [{plugin_name}] loaded.')
            except ImportError as e:
                bot.logger.error(
                    f'Import error: can not import [{plugin_name}], because {e}'
                )


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
