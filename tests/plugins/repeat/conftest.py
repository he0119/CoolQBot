import pytest
from nonebug import App
from sqlalchemy import delete


@pytest.fixture
async def app(app: App):
    yield app

    # 清理数据库
    from nonebot_plugin_datastore.db import create_session

    from src.plugins.repeat.models import Enabled, Record

    async with create_session() as session, session.begin():
        await session.execute(delete(Record))
        await session.execute(delete(Enabled))
