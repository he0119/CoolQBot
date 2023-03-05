import pytest
from nonebug import App
from sqlalchemy import delete
from sqlalchemy.ext.asyncio.session import AsyncSession


@pytest.fixture
async def app(app: App):
    yield app

    # 清理数据库
    from nonebot_plugin_datastore.db import create_session

    from src.plugins.cyber_hospital.model import Patient, Record

    async with create_session() as session, session.begin():
        await session.execute(delete(Patient))
        await session.execute(delete(Record))


@pytest.fixture
async def session(app: App):
    from nonebot_plugin_datastore.db import create_session

    async with create_session() as session:
        yield session
