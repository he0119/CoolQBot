from pathlib import Path

import nonebot
import pytest
from loguru import logger
from nonebug import NONEBOT_INIT_KWARGS
from nonebug.app import App
from pytest_mock import MockerFixture
from sqlalchemy import StaticPool, delete


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
        "sqlalchemy_database_url": "sqlite+aiosqlite:///:memory:",
        "sqlalchemy_engine_options": {"poolclass": StaticPool},
        "alembic_startup_check": False,
    }


@pytest.fixture(scope="session")
def load_plugin(nonebug_init: None):
    from nonebot.adapters.onebot.v11 import Adapter

    driver = nonebot.get_driver()
    driver.register_adapter(Adapter)

    nonebot.require("nonebot_plugin_localstore")
    nonebot.require("nonebot_plugin_apscheduler")
    nonebot.require("nonebot_plugin_saa")
    nonebot.require("nonebot_plugin_alconna")
    nonebot.require("nonebot_plugin_session")
    nonebot.require("nonebot_plugin_userinfo")
    nonebot.require("nonebot_plugin_user")

    nonebot.load_plugins(str(Path(__file__).parent.parent / "src" / "plugins"))


@pytest.fixture
async def app(tmp_path: Path, load_plugin, mocker: MockerFixture):
    from nonebot_plugin_orm import init_orm

    driver = nonebot.get_driver()
    # 清除连接钩子，现在 NoneBug 会自动触发 on_bot_connect
    driver._bot_connection_hook.clear()

    # 插件数据目录
    mocker.patch("nonebot_plugin_localstore.BASE_DATA_DIR", tmp_path / "data")
    mocker.patch("nonebot_plugin_localstore.BASE_CACHE_DIR", tmp_path / "cache")
    mocker.patch("nonebot_plugin_localstore.BASE_CONFIG_DIR", tmp_path / "config")

    await init_orm()

    return App()


@pytest.fixture
def caplog(caplog):
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


@pytest.fixture
async def default_user(app: App):
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_user.models import Bind, User

    async with get_session() as session:
        user = User(id=1, name="nickname")
        user2 = User(id=2, name="nickname10000")
        session.add(user)
        session.add(user2)
        bind = Bind(platform_id=10, platform="qq", bind_user=user, original_user=user)
        bind2 = Bind(
            platform_id=10000, platform="qq", bind_user=user2, original_user=user2
        )
        session.add(bind)
        session.add(bind2)
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
    user_info2 = UserInfo(
        user_id="10000",
        user_name="nickname10000",
        user_displayname="card10000",
        user_remark=None,
        user_avatar=QQAvatar(qq=10000),
        user_gender="unknown",
    )
    # 默认为 fake 适配器
    _user_info_cache["qq_fake_test_10000_10_10"] = user_info
    _user_info_cache["qq_fake_test_10000_10000_10000"] = user_info2
    # 需要 onebot 11 适配器才能使用 alconna，因为其不支持 fake 适配器
    _user_info_cache["qq_OneBot V11_test_10000_10_10"] = user_info
    _user_info_cache["qq_OneBot V11_test_10000_10000_10000"] = user_info2

    yield

    # 清除数据库
    async with get_session() as session, session.begin():
        await session.execute(delete(User))
        await session.execute(delete(Bind))
