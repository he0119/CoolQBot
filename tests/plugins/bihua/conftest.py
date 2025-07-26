from pathlib import Path

import pytest
from nonebug import App
from pytest_mock import MockerFixture


@pytest.fixture
async def app(app: App, tmp_path: Path, mocker: MockerFixture):
    """清理壁画数据"""
    mocker.patch("src.plugins.bihua.utils.DATA_DIR", tmp_path / "data" / "bihua")

    yield app

    # 清理数据
    from nonebot_plugin_orm import get_session
    from sqlalchemy import delete

    from src.plugins.bihua.model import Bihua

    async with get_session() as session, session.begin():
        await session.execute(delete(Bihua))
