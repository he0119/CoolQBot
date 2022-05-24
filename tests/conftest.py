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
    config.datastore_cache_dir = tmp_path / "cache"
    config.datastore_config_dir = tmp_path / "config"
    config.datastore_data_dir = tmp_path / "data"

    # 加载插件
    if param:
        if param == "all":
            nonebot.load_from_toml("pyproject.toml")
        else:
            for plugin in param:
                nonebot.load_plugin(plugin)

    return App(monkeypatch)


@pytest.fixture
async def session(app: App):
    from nonebot_plugin_datastore.db import get_engine, init_db
    from sqlmodel.ext.asyncio.session import AsyncSession

    await init_db()

    async with AsyncSession(get_engine()) as session:
        yield session
