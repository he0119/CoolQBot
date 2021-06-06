""" 插件数据
"""
import configparser
import os
import pickle
from pathlib import Path
from typing import IO, Any

from nonebot import get_driver


class ConfigData:
    """ 插件配置管理 """
    def __init__(self, path: Path) -> None:
        self._path = path
        self._config = configparser.ConfigParser()
        if self._path.exists():
            self._load_config()
        else:
            self._save_config()

    def _load_config(self) -> None:
        """ 读取配置 """
        self._config.read(self._path, encoding='utf8')

    def _save_config(self) -> None:
        """ 保存配置 """
        with open(self._path, 'w', encoding='utf8') as conf:
            self._config.write(conf)

    def get(self, section: str, option: str, fallback: str = '') -> str:
        """ 获得配置

        如果配置不存在则使用 `fallback` 并保存
        如果不提供 `fallback` 默认返回空字符串
        """
        try:
            value = self._config.get(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            value = fallback
            # 保存默认配置
            if section not in self._config.sections():
                self._config[section] = {}
            self._config.set(section, option, fallback)
            self._save_config()
        return value

    def set(self, section: str, option: str, value: str) -> None:
        """ 设置配置 """
        if section not in self._config.sections():
            self._config[section] = {}
        self._config.set(section, option, value)
        self._save_config()


class PluginData:
    """ 插件数据管理
    将插件数据保存在 `data` 文件夹对应的目录下。
    提供保存和读取文件/数据的方法。
    """
    def __init__(self, name: str) -> None:
        # 插件名，用来确定插件的文件夹位置
        self._name = name
        self._base_path: Path = get_driver(
        ).config.data_dir_path / f'plugin-{name}'

        # 如果文件夹不存在则自动新建
        os.makedirs(self._base_path, exist_ok=True)

        # 插件配置
        self._config = None

    @property
    def config(self) -> ConfigData:
        """ 获取配置管理 """
        if not self._config:
            self._config = ConfigData(self._base_path / f'{self._name}.ini')
        return self._config

    def save_pkl(self, data: object, filename: str) -> None:
        with self.open(f'{filename}.pkl', 'wb') as f:
            pickle.dump(data, f)

    def load_pkl(self, filename: str) -> Any:
        with self.open(f'{filename}.pkl', 'rb') as f:
            data = pickle.load(f)
        return data

    def open(self, filename: str, open_mode: str = 'r', encoding=None) -> IO:
        path = self._base_path / filename
        return open(path, open_mode, encoding=encoding)

    def exists(self, filename: str) -> bool:
        """ 判断文件是否存在
        """
        path = self._base_path / filename
        return path.exists()
