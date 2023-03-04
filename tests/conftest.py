from pathlib import Path
from typing import TYPE_CHECKING

import nonebot
import pytest
from nonebug import NONEBOT_INIT_KWARGS
from nonebug.app import App
from sqlalchemy import delete

if TYPE_CHECKING:
    from nonebot.plugin import Plugin


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "datastore_database_url": "sqlite+aiosqlite:///:memory:"
    }


@pytest.fixture(scope="session", autouse=True)
def load_plugin(nonebug_init: None) -> set["Plugin"]:
    return nonebot.load_plugins(str(Path(__file__).parent.parent / "src" / "plugins"))


@pytest.fixture
async def app(nonebug_init: None, tmp_path: Path):
    from nonebot_plugin_datastore.config import plugin_config
    from nonebot_plugin_datastore.db import create_session, init_db

    # 插件数据目录
    plugin_config.datastore_cache_dir = tmp_path / "cache"
    plugin_config.datastore_config_dir = tmp_path / "config"
    plugin_config.datastore_data_dir = tmp_path / "data"

    await init_db()

    yield App()

    # 清理数据库
    from src.plugins.ff14.plugins.ff14_fflogs.models import User as FFLogsUser

    async with create_session() as session, session.begin():
        await session.execute(delete(FFLogsUser))
