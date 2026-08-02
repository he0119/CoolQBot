"""llm 插件测试的公共配置

每个测试结束后清空群组配置表，避免会话 ID 在测试间互相污染。
"""

import pytest
from nonebug import App
from sqlalchemy import delete


@pytest.fixture
async def app(app: App):
    yield app
    from nonebot_plugin_orm import get_session

    from src.plugins.llm.models import GroupLLMConfig

    async with get_session() as session, session.begin():
        await session.execute(delete(GroupLLMConfig))
