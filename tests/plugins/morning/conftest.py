import pytest
from nonebug import App
from sqlalchemy import delete


@pytest.fixture
async def app(app: App):
    yield app

    # 清理数据库
    from nonebot_plugin_datastore.db import create_session

    from src.plugins.morning.plugins.hello.models import Hello
    from src.plugins.morning.plugins.morning_greeting.models import MorningGreeting

    async with create_session() as session, session.begin():
        await session.execute(delete(Hello))
        await session.execute(delete(MorningGreeting))
