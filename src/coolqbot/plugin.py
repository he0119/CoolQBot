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
    """ TODO:一个插件应该只能访问`data`文件夹下面一个的文件夹，用来存放各种各样的配置和文件

    这个应该由插件自己管理，插件也只能通过这个类来访问和修改属于自己的数据(配置或者文件)
    一个插件不一定需要配置文件，也不一定需要数据文件，这个由插件自己决定。
    """
    def __init__(self, name):
        # 插件名，用来确定插件的文件夹位置
        self._name = name

    def save_pkl(self, data, path):
        with path.open(mode='wb') as f:
            pickle.dump(data, f)

    def load_pkl(self, path):
        with path.open(mode='rb') as f:
            data = pickle.load(f)
        return data

    def load_config(self):
        pass

    def save_config(self):
        pass

    def open(self, path):
        pass
