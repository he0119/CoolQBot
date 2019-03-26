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

    将插件数据保存在 `data` 文件夹对应的目录下。
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
            self._config_path = self._base_path / f'{self._name}.conf'
            self.config = configparser.ConfigParser()
            if self._config_path.exists():
                self._load_config()
            else:
                self._save_config()

    def save_pkl(self, data, filename):
        with self.open(filename, 'wb') as f:
            pickle.dump(data, f)

    def load_pkl(self, filename):
        with self.open(filename, 'rb') as f:
            data = pickle.load(f)
        return data

    def config_get(self, section, option, fallback=None):
        """ 获得配置

        如果配置不存在则使用`fallback`并保存
        """
        try:
            value = self.config.get(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if not fallback:
                raise
            value = fallback
            # 保存默认配置
            if section not in self.config.sections():
                self.config[section] = {}
            self.config.set(section, option, fallback)
            self._save_config()
        return value

    def config_set(self, section, option, value):
        """ 设置配置
        """
        if section not in self.config.sections():
            self.config[section] = {}
        self.config.set(section, option, value)
        self._save_config()

    def _load_config(self):
        """ 读取配置
        """
        self.config.read(self._config_path)

    def _save_config(self):
        """ 保存配置
        """
        with self.open(self._config_path, 'w') as configfile:
            self.config.write(configfile)

    def open(self, filename, open_mode='r'):
        path = self._base_path / filename
        return open(path, open_mode)

    def exists(self, filename):
        """ 判断文件是否存在
        """
        path = self._base_path / filename
        return path.exists()
