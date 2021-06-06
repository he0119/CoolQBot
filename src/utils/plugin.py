""" 插件数据
"""
import configparser
import json
import os
import pickle
from pathlib import Path
from typing import IO, Any, Optional

import httpx
from nonebot import get_driver
from nonebot.log import logger


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


class NetworkFile:
    """ 从网络获取文件

    暂时只支持 json 格式
    """
    def __init__(self, url: str, filename: str,
                 plugin_data: "PluginData") -> None:
        self._url = url
        self._filename = filename
        self._plugin_data = plugin_data

        self._data = None

    async def load_from_network(self) -> Optional[dict]:
        """ 从网络加载文件 """
        logger.info('正在从网络获取数据')
        async with httpx.AsyncClient() as client:
            r = await client.get(self._url, timeout=30)
            rjson = r.json()
            # 同时保存一份文件在本地，以后就不用从网络获取
            with self._plugin_data.open(
                    self._filename,
                    open_mode='w',
                    encoding='utf8',
            ) as f:
                json.dump(rjson, f, ensure_ascii=False, indent=2)
            logger.info('已保存数据至本地')
            return rjson

    def load_from_local(self) -> Optional[dict]:
        """ 从本地获取数据 """
        logger.info('正在加载本地数据')
        if self._plugin_data.exists(self._filename):
            with self._plugin_data.open(self._filename, encoding='utf8') as f:
                return json.load(f)

    @property
    async def data(self) -> Optional[dict]:
        """ 数据

        先从本地加载，如果失败则从仓库加载
        """
        if not self._data:
            self._data = self.load_from_local()
        if not self._data:
            self._data = await self.load_from_network()
        return self._data

    async def update(self) -> None:
        """ 从网络更新数据 """
        self._data = await self.load_from_network()


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
        """ 判断文件是否存在 """
        path = self._base_path / filename
        return path.exists()

    def network_file(self, url: str, filename: str):
        """ 网络文件

        从网络上获取数据，并缓存至本地，仅支持 json 格式
        """
        return NetworkFile(url, filename, self)
