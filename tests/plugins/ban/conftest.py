import pytest
from nonebug import App


@pytest.fixture
async def app(app: App, _default_user):
    yield app

    from src.plugins.ban import _bot_role

    # 清空机器人角色缓存
    _bot_role.clear()
