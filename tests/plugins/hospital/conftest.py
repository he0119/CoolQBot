import pytest
from nonebug import App
from sqlalchemy import delete


@pytest.fixture
async def app(app: App, default_user):
    yield app

    # 清理数据库
    from nonebot_plugin_orm import get_session

    from src.plugins.cyber_hospital.model import Patient, Record

    async with get_session() as session, session.begin():
        await session.execute(delete(Patient))
        await session.execute(delete(Record))


@pytest.fixture
async def session(app: App):
    from nonebot_plugin_orm import get_session

    async with get_session() as session:
        yield session
