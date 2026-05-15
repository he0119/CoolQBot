import pytest
from nonebug import App
from sqlalchemy import delete


@pytest.fixture
async def app(app: App):
    yield app
    from nonebot_plugin_orm import get_session

    from src.plugins.llm_quota.models import GroupQuotaConfig

    async with get_session() as session, session.begin():
        await session.execute(delete(GroupQuotaConfig))
