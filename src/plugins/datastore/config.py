from pathlib import Path

from nonebot import get_driver, require
from pydantic import BaseModel, Extra

store = require("nonebot_plugin_localstore")

# 默认目录
cache_dir: str = store.get_cache_dir("datastore")
data_dir: str = store.get_data_dir("datastore")


class Config(BaseModel, extra=Extra.ignore):
    cache_dir: Path = Path(cache_dir)
    data_dir: Path = Path(data_dir)
    database_url: str = f"sqlite+aiosqlite:///{data_dir}/data.db"
    """ 数据库连接字符串

    默认使用 sqlite
    """


plugin_config = Config.parse_obj(get_driver().config.dict())
