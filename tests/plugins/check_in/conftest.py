import pytest
from nonebug import App
from sqlalchemy import delete


@pytest.fixture
async def app(app: App, _default_user):
    yield app

    # 清理数据库
    from nonebot_plugin_orm import get_session

    from src.plugins.check_in.models import (
        BodyFatRecord,
        DietaryRecord,
        FitnessRecord,
        UserInfo,
        WeightRecord,
    )

    async with get_session() as session, session.begin():
        await session.execute(delete(UserInfo))
        await session.execute(delete(WeightRecord))
        await session.execute(delete(BodyFatRecord))
        await session.execute(delete(DietaryRecord))
        await session.execute(delete(FitnessRecord))


@pytest.fixture
async def session(app: App):
    from nonebot_plugin_orm import get_session

    async with get_session() as session:
        yield session
