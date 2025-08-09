import pytest
from nonebug import App
from sqlalchemy import delete


@pytest.fixture
async def app(app: App):
    yield app

    # 清理数据库
    from nonebot_plugin_orm import get_session

    from src.plugins.repeat.models import Enabled, MessageRecord
    from src.plugins.repeat.recorder import get_recorder

    # 清除 lru_cache 缓存
    get_recorder.cache_clear()

    async with get_session() as session, session.begin():
        await session.execute(delete(MessageRecord))
        await session.execute(delete(Enabled))
