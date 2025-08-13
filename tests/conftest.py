import sys
from pathlib import Path

import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from nonebot.adapters.qq import Adapter as QQAdapter
from nonebug import NONEBOT_INIT_KWARGS, NONEBOT_START_LIFESPAN
from nonebug.app import App
from pytest_asyncio import is_async_test
from pytest_mock import MockerFixture
from sqlalchemy import delete

HOME_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOME_DIR))


def pytest_configure(config: pytest.Config) -> None:
    config.stash[NONEBOT_INIT_KWARGS] = {
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
        "alconna_cache_message": False,
    }
    # 如果不设置为 False，会运行插件的 on_startup 函数
    # 会导致 orm 的 init_orm 函数在 patch 之前被调用
    config.stash[NONEBOT_START_LIFESPAN] = False


def pytest_collection_modifyitems(items: list[pytest.Item]):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init(after_nonebot_init: None):
    # 加载适配器
    driver = nonebot.get_driver()
    driver.register_adapter(OneBotV11Adapter)
    driver.register_adapter(QQAdapter)

    # 替换内置权限
    from src.utils.permission import patch_permission

    patch_permission()

    # 加载插件
    nonebot.load_plugins(str(HOME_DIR / "src" / "plugins"))


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
    mocker.patch("nonebot_plugin_orm._data_dir", tmp_path)

    await init_orm()

    return app


@pytest.fixture(autouse=True)
async def _default_user(app: App):
    """设置默认用户名"""

    # 添加 user 缓存
    from nonebot_plugin_user.utils import get_user, set_user_email, set_user_name

    await get_user("QQClient", "10")
    await set_user_name("QQClient", "10", "nickname")
    await set_user_email("QQClient", "10", "nickname@example.com")
    await get_user("QQClient", "10000")
    await set_user_name("QQClient", "10000", "nickname10000")

    # 添加 uninfo 缓存
    from nonebot_plugin_uninfo import Member, Scene, SceneType, Session, User
    from nonebot_plugin_uninfo.adapters import INFO_FETCHER_MAPPING

    uninfo_cache = INFO_FETCHER_MAPPING["OneBot V11"].session_cache
    uninfo_cache["group_10000_10"] = Session(
        self_id="123456",
        adapter="OneBot V11",
        scope="QQClient",
        scene=Scene(
            id="10000",
            type=SceneType.GROUP,
        ),
        user=User(id="10", name="nickname"),
        member=Member(
            user=User(id="10", name="nickname"),
        ),
    )
    uninfo_cache["group_10000_10000"] = Session(
        self_id="123456",
        adapter="OneBot V11",
        scope="QQClient",
        scene=Scene(
            id="10000",
            type=SceneType.GROUP,
        ),
        user=User(id="10000", name="nickname10000"),
        member=Member(
            user=User(id="10000", name="nickname10000"),
        ),
    )

    yield

    # 清除数据库
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_user.models import Bind, User

    async with get_session() as session, session.begin():
        await session.execute(delete(User))
        await session.execute(delete(Bind))
