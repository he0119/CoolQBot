import pytest
from nonebug import App
from sqlalchemy import delete


@pytest.fixture
async def app(app: App):
    yield app

    # 清理数据库
    from nonebot_plugin_orm import get_session

    from src.plugins.alisten.models import AlistenConfig

    async with get_session() as session, session.begin():
        await session.execute(delete(AlistenConfig))
