from pathlib import Path
from typing import Optional

from nonebot import get_driver, require
from pydantic import BaseModel, Extra

store = require("nonebot_plugin_localstore")

# 默认目录
BASE_CACHE_DIR: Path = Path(store.get_cache_dir(""))
BASE_CONFIG_DIR: Path = Path(store.get_config_dir(""))
BASE_DATA_DIR: Path = Path(store.get_data_dir(""))


class Config(BaseModel, extra=Extra.ignore):
    cache_dir: Path = BASE_CACHE_DIR
    config_dir: Path = BASE_CONFIG_DIR
    data_dir: Path = BASE_DATA_DIR
    database_url: Optional[str]

    @property
    def real_database_url(self) -> str:
        """数据库连接字符串

        默认使用 SQLite
        """
        if self.database_url:
            return self.database_url

        return f"sqlite+aiosqlite:///{self.data_dir / 'data.db'}"


plugin_config = Config.parse_obj(get_driver().config.dict())
