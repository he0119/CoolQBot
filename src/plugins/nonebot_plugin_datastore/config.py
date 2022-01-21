from pathlib import Path
from typing import Dict

from nonebot import get_driver, require
from pydantic import BaseModel, Extra, root_validator

store = require("nonebot_plugin_localstore")

# 默认目录
BASE_CACHE_DIR: Path = Path(store.get_cache_dir(""))
BASE_CONFIG_DIR: Path = Path(store.get_config_dir(""))
BASE_DATA_DIR: Path = Path(store.get_data_dir(""))


class Config(BaseModel, extra=Extra.ignore):
    cache_dir: Path = BASE_CACHE_DIR
    config_dir: Path = BASE_CONFIG_DIR
    data_dir: Path = BASE_DATA_DIR
    database_url: str
    """数据库连接字符串

    默认使用 SQLite
    """

    @root_validator(pre=True, allow_reuse=True)
    def set_database_url(cls, values: Dict):
        database_url = values.get("database_url")
        data_dir = values.get("data_dir")
        if database_url is None:
            if data_dir is None:
                data_dir = BASE_DATA_DIR
            else:
                data_dir = Path(data_dir)
            values["database_url"] = f"sqlite+aiosqlite:///{data_dir / 'data.db'}"
        return values


plugin_config = Config.parse_obj(get_driver().config.dict())
