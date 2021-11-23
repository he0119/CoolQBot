from pathlib import Path

import nonebot
import nonebug
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
def bug(tmpdir):
    """初始化测试"""
    # 添加额外的配置
    home_dir_path = Path(tmpdir).resolve()
    # 插件数据目录
    data_dir_path = home_dir_path / "data"

    nonebug.init(home_dir_path=home_dir_path, data_dir_path=data_dir_path)


@pytest.fixture
def plugin(request, bot):
    plugin = nonebot.load_plugin(f"src.plugins.{request.param}")
    assert plugin is not None
    return plugin
