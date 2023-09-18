import datetime
from contextlib import contextmanager

import pytest
from freezegun import freeze_time
from nonebug import App
from sqlalchemy import delete, event


@pytest.fixture
async def app(app: App):
    # UserInfo 有自己的缓存，所以要清理
    from nonebot_plugin_userinfo.getter import _user_info_cache

    _user_info_cache.clear()

    yield app

    # 清理数据库
    from nonebot_plugin_datastore.db import create_session

    from src.plugins.user.models import Bind, User

    async with create_session() as session, session.begin():
        await session.execute(delete(Bind))
        await session.execute(delete(User))


@pytest.fixture
async def session(app: App):
    from nonebot_plugin_datastore.db import create_session

    async with create_session() as session:
        yield session


# https://stackoverflow.com/questions/29116718/how-to-mocking-created-time-in-sqlalchemy
@contextmanager
def patch_time(time_to_freeze, tick=True):
    from src.plugins.user.models import User

    with freeze_time(time_to_freeze, tick=tick) as frozen_time:

        def set_timestamp(mapper, connection, target):
            now = datetime.datetime.utcnow()
            if hasattr(target, "created_at"):
                target.created_at = now

        event.listen(User, "before_insert", set_timestamp, propagate=True)
        yield frozen_time
        event.remove(User, "before_insert", set_timestamp)


@pytest.fixture(scope="function")
def patch_current_time():
    return patch_time
