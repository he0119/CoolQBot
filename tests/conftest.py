from pathlib import Path

import nonebot
import pytest


@pytest.fixture
def bot(tmpdir):
    """初始化机器人"""
    nonebot.init()
    # 添加额外的配置
    config = nonebot.get_driver().config
    config.home_dir_path = Path(tmpdir).resolve()
    # 插件数据目录
    config.data_dir_path = config.home_dir_path / "data"


@pytest.fixture
def plugin(request, bot):
    plugin = nonebot.load_plugin(f"src.plugins.{request.param}")
    assert plugin is not None
    return plugin
