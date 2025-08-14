import pytest
from nonebug import App


@pytest.fixture
async def app(app: App):
    """清理群组绑定数据"""
    yield app

    # 清理数据
    from nonebot_plugin_orm import get_session
    from sqlalchemy import delete

    from src.utils.group_bind.model import GroupBind

    async with get_session() as session, session.begin():
        await session.execute(delete(GroupBind))
