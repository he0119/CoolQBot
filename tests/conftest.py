from pathlib import Path

import nonebot
import pytest


@pytest.fixture
def plugin(request, tmpdir):
    nonebot.init()
    # 添加额外的配置
    config = nonebot.get_driver().config
    config.home_dir_path = Path(tmpdir).resolve()
    # 插件数据目录
    config.data_dir_path = config.home_dir_path / "data"

    nonebot.load_plugins(f"src/plugins")
    plugins = nonebot.get_loaded_plugins()
    plugin = list(filter(lambda x: x.name == request.param, plugins))[0]

    return plugin
