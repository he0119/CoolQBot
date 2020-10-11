""" 插件数据
"""
import configparser
import pickle
from typing import IO, NoReturn

from _typeshed import OpenTextMode
from nonebot import get_driver


class PluginData:
    """ 插件数据管理
    将插件数据保存在 `data` 文件夹对应的目录下。
    提供保存和读取文件/数据的方法。
    """
    def __init__(self, name: str, config: bool = False) -> NoReturn:
        # 插件名，用来确定插件的文件夹位置
        self._name = name
        self._base_path = get_driver().config.data_dir_path / f'plugin-{name}'

        # 如果文件夹不存在则自动新建
        if not get_driver().config.data_dir_path.exists():
            get_driver().config.data_dir_path.mkdir()
        if not self._base_path.exists():
            self._base_path.mkdir()

        # 如果需要则初始化并加载配置
        if config:
            self._config_path = self._base_path / f'{self._name}.ini'
            self.config = configparser.ConfigParser()
            if self._config_path.exists():
                self._load_config()
            else:
                self._save_config()

    def save_pkl(self, data: object, filename: str) -> NoReturn:
        with self.open(f'{filename}.pkl', 'wb') as f:
            pickle.dump(data, f)

    def load_pkl(self, filename: str) -> object:
        with self.open(f'{filename}.pkl', 'rb') as f:
            data = pickle.load(f)
        return data

    def get_config(self, section: str, option: str, fallback: str = '') -> str:
        """ 获得配置
        如果配置不存在则使用 `fallback` 并保存
        如果不提供 `fallback` 默认返回空字符串
        """
        try:
            value = self.config.get(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            value = fallback
            # 保存默认配置
            if section not in self.config.sections():
                self.config[section] = {}
            self.config.set(section, option, fallback)
            self._save_config()
        return value

    def set_config(self, section: str, option: str, value: str) -> NoReturn:
        """ 设置配置
        """
        if section not in self.config.sections():
            self.config[section] = {}
        self.config.set(section, option, value)
        self._save_config()

    def _load_config(self) -> NoReturn:
        """ 读取配置
        """
        self.config.read(self._config_path)

    def _save_config(self) -> NoReturn:
        """ 保存配置
        """
        with self.open(self._config_path, 'w') as configfile:
            self.config.write(configfile)

    def open(self, filename: str, open_mode: OpenTextMode = 'r') -> IO:
        path = self._base_path / filename
        return open(path, open_mode)

    def exists(self, filename: str) -> bool:
        """ 判断文件是否存在
        """
        path = self._base_path / filename
        return path.exists()
