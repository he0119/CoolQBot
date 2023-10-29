import pytest
from nonebug import App
from sqlalchemy import delete


@pytest.fixture
async def app(app: App):
    yield app

    # 清理数据库
    from nonebot_plugin_datastore.db import get_session

    from src.plugins.repeat.models import Enabled, MessageRecord
    from src.plugins.repeat.recorder import Singleton

    Singleton._instances.clear()

    async with get_session() as session, session.begin():
        await session.execute(delete(MessageRecord))
        await session.execute(delete(Enabled))
