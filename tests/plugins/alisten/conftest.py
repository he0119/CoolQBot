import pytest
from nonebug import App
from pytest_mock import MockerFixture
from sqlalchemy import delete


@pytest.fixture
async def app(app: App):
    yield app

    # 清理数据库
    from nonebot_plugin_orm import get_session

    from src.plugins.alisten.models import AlistenConfig

    async with get_session() as session, session.begin():
        await session.execute(delete(AlistenConfig))


@pytest.fixture
async def _configs(app: App, mocker: MockerFixture):
    from nonebot_plugin_orm import get_session

    from src.plugins.alisten.models import AlistenConfig

    async with get_session() as session:
        session.add(
            AlistenConfig(
                session_id="QQClient_10000",
                server_url="http://localhost:8080",
                house_id="room123",
                house_password="password123",
            )
        )
        await session.commit()
