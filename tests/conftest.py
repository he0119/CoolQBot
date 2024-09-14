import sys
from pathlib import Path

import nonebot
import pytest
from nonebug import NONEBOT_INIT_KWARGS
from nonebug.app import App
from pytest_mock import MockerFixture
from sqlalchemy import StaticPool, delete

home_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(home_dir))


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "sqlalchemy_database_url": "sqlite+aiosqlite:///:memory:",
        "sqlalchemy_engine_options": {"poolclass": StaticPool},
        "alembic_startup_check": False,
        "superusers": ["nickname"],
        "qq_bots": [
            {
                "id": "123456",
                "nickname": "nickname",
                "token": "token",
                "secret": "secret",
            },
        ],
    }


@pytest.fixture(scope="session", autouse=True)
def _load_plugin(nonebug_init: None):
    from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
    from nonebot.adapters.qq import Adapter as QQAdapter

    driver = nonebot.get_driver()
    driver.register_adapter(OneBotV11Adapter)
    driver.register_adapter(QQAdapter)

    nonebot.require("nonebot_plugin_localstore")
    nonebot.require("nonebot_plugin_datastore")
    nonebot.require("nonebot_plugin_orm")
    nonebot.require("nonebot_plugin_apscheduler")
    nonebot.require("nonebot_plugin_saa")
    nonebot.require("nonebot_plugin_alconna")
    nonebot.require("nonebot_plugin_user")

    nonebot.load_plugins(str(Path(__file__).parent.parent / "src" / "plugins"))


@pytest.fixture
async def app(app: App, tmp_path: Path, mocker: MockerFixture):
    from nonebot_plugin_datastore.config import plugin_config
    from nonebot_plugin_orm import init_orm

    driver = nonebot.get_driver()
    # 清除连接钩子，现在 NoneBug 会自动触发 on_bot_connect
    driver._bot_connection_hook.clear()

    # 插件数据目录
    mocker.patch.object(plugin_config, "datastore_cache_dir", tmp_path / "cache")
    mocker.patch.object(plugin_config, "datastore_config_dir", tmp_path / "config")
    mocker.patch.object(plugin_config, "datastore_data_dir", tmp_path / "data")
    mocker.patch("nonebot_plugin_localstore.BASE_DATA_DIR", tmp_path / "data")
    mocker.patch("nonebot_plugin_localstore.BASE_CACHE_DIR", tmp_path / "cache")
    mocker.patch("nonebot_plugin_localstore.BASE_CONFIG_DIR", tmp_path / "config")
    mocker.patch("nonebot_plugin_orm._data_dir", tmp_path / "orm")

    await init_orm()

    return app


@pytest.fixture
async def _default_user(app: App):
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_user.models import Bind, User
    from nonebot_plugin_user.utils import get_user, set_user_name

    await get_user("qq", "10")
    await set_user_name("qq", "10", "nickname")
    await get_user("qq", "10000")
    await set_user_name("qq", "10000", "nickname10000")

    yield

    # 清除数据库
    async with get_session() as session, session.begin():
        await session.execute(delete(User))
        await session.execute(delete(Bind))
