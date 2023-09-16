from pathlib import Path

import nonebot
import pytest
from loguru import logger
from nonebug import NONEBOT_INIT_KWARGS
from nonebug.app import App
from sqlalchemy import delete


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "datastore_database_url": "sqlite+aiosqlite:///:memory:"
    }


@pytest.fixture(scope="session", autouse=True)
def load_plugin(nonebug_init: None):
    from nonebot.adapters.onebot.v11 import Adapter

    driver = nonebot.get_driver()
    driver.register_adapter(Adapter)

    nonebot.load_plugin("nonebot_plugin_datastore")
    nonebot.load_plugin("nonebot_plugin_apscheduler")
    nonebot.load_plugin("nonebot_plugin_saa")
    nonebot.load_plugin("nonebot_plugin_alconna")
    nonebot.load_plugin("nonebot_plugin_session")
    nonebot.load_plugin("nonebot_plugin_userinfo")

    nonebot.load_plugins(str(Path(__file__).parent.parent / "src" / "plugins"))


@pytest.fixture
async def app(nonebug_init: None, tmp_path: Path):
    from nonebot_plugin_datastore.config import plugin_config
    from nonebot_plugin_datastore.db import init_db

    driver = nonebot.get_driver()
    # 清除连接钩子，现在 NoneBug 会自动触发 on_bot_connect
    driver._bot_connection_hook.clear()

    # 插件数据目录
    plugin_config.datastore_cache_dir = tmp_path / "cache"
    plugin_config.datastore_config_dir = tmp_path / "config"
    plugin_config.datastore_data_dir = tmp_path / "data"

    await init_db()

    return App()


@pytest.fixture
def caplog(caplog):
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


@pytest.fixture
async def default_user(app: App):
    from nonebot_plugin_datastore import create_session

    from src.plugins.user.models import Bind, User

    async with create_session() as session:
        user = User(id=1, name="nickname")
        session.add(user)
        bind = Bind(pid=10, platform="qq", auser=user, buser=user)
        session.add(bind)
        await session.commit()

    # 设置 UserInfo 缓存
    from nonebot_plugin_userinfo import UserInfo
    from nonebot_plugin_userinfo.getter import _user_info_cache
    from nonebot_plugin_userinfo.image_source import QQAvatar

    user_info = UserInfo(
        user_id="10",
        user_name="nickname",
        user_displayname="card",
        user_remark=None,
        user_avatar=QQAvatar(qq=10),
        user_gender="unknown",
    )
    # 默认为 fake 适配器
    _user_info_cache["qq_fake_test_10000_10_10"] = user_info
    # 需要 onebot 11 适配器才能使用 alconna，因为其不支持 fake 适配器
    _user_info_cache["qq_OneBot V11_test_10000_10_10"] = user_info

    yield

    # 清除数据库
    async with create_session() as session, session.begin():
        await session.execute(delete(User))
        await session.execute(delete(Bind))
