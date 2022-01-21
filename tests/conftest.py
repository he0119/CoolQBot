from pathlib import Path

import pytest
from nonebug.app import App


@pytest.fixture
def app(
    nonebug_init: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request,
) -> App:
    param = getattr(request, "param", ())

    import nonebot

    config = nonebot.get_driver().config
    # 插件数据目录
    config.cache_dir = tmp_path / "cache"
    config.data_dir = tmp_path / "data"
    config.database_url = f"sqlite+aiosqlite:///{tmp_path}/data.db"

    # 加载插件
    # 默认加载所有插件
    if param:
        for plugin in param:
            nonebot.load_plugin(plugin)
    else:
        nonebot.load_from_toml("pyproject.toml")

    return App(monkeypatch)


@pytest.fixture
async def session(app: App):
    from sqlmodel.ext.asyncio.session import AsyncSession

    from src.plugins.nonebot_plugin_datastore.db import engine, init_db

    await init_db()

    async with AsyncSession(engine) as session:
        yield session
