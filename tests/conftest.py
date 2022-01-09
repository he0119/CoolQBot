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
    config.home_dir_path = tmp_path
    # 插件数据目录
    config.data_dir_path = config.home_dir_path / "data"

    # 加载插件
    # 默认加载所有插件
    if param:
        for plugin in param:
            nonebot.load_plugin(plugin)
    else:
        nonebot.load_from_toml("pyproject.toml")

    return App(monkeypatch)
