""" 插件相关
"""
import configparser
import os
import pickle

from coolqbot.bot import bot
from coolqbot.config import DATA_DIR_PATH, PLUGINS_DIR_PATH


class PluginManager:
    """ 插件管理器
    """

    def __init__(self):
        self._plugin_prefix = 'plugins'

    def _get_plugin_name(self, name):
        return f'{self._plugin_prefix}.{name}'

    def load_plugin(self):
        filenames = [x.stem for x in PLUGINS_DIR_PATH.iterdir() if x.is_file()]
        for plugin_name in filenames:
            try:
                __import__(self._get_plugin_name(plugin_name))
                bot.logger.debug(f'Plugin [{plugin_name}] loaded.')
            except ImportError as e:
                bot.logger.error(
                    f'Import error: can not import [{plugin_name}], because {e}'
                )


class PluginData:
    """ 插件数据管理

    将插件数据保存在对应的`data`文件夹下。
    提供保存和读取文件/数据的方法。
    """

    def __init__(self, name, config=False):
        # 插件名，用来确定插件的文件夹位置
        self._name = name
        self._base_path = DATA_DIR_PATH / f'plugin-{name}'
        # 如果文件夹不存在则自动新建
        if not DATA_DIR_PATH.exists():
            DATA_DIR_PATH.mkdir()
        if not self._base_path.exists():
            self._base_path.mkdir()
        # 如果需要则初始化并加载配置
        if config:
            self.config = configparser.ConfigParser()
            self._load_config()

    def save_pkl(self, data, filename):
        with self.open(filename, 'wb') as f:
            pickle.dump(data, f)

    def load_pkl(self, filename):
        with self.open(filename, 'rb') as f:
            data = pickle.load(f)
        return data

    def _load_config(self):
        path = self._base_path / f'{self._name}.conf'
        self.config.read(path)

    def _save_config(self):
        filename = f'{self._name}.conf'
        with self.open(filename, 'w') as configfile:
            self.config.write(configfile)

    def open(self, filename, open_mode='r'):
        path = self._base_path / filename
        return open(path, open_mode)

    def exists(self, filename):
        """ 判断文件是否存在
        """
        path = self._base_path / filename
        return path.exists()
