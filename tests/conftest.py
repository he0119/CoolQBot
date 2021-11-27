from pathlib import Path

import nonebot
import nonebug
import pytest
from nonebot.plugin import plugins


@pytest.fixture
def bot(tmp_path):
    """初始化机器人"""
    # 插件数据目录
    data_path = tmp_path / "data"
    # nonebug 目录
    nonebug_path = tmp_path / "nonebug"

    # 添加额外的配置
    nonebug.init(
        home_dir_path=tmp_path,
        data_dir_path=data_path,
        nonebug_log_dir=str(nonebug_path),
    )


@pytest.fixture
def nonebug_path(bot):
    """初始化测试"""
    nonebug_path = nonebot.get_driver().config.nonebug_log_dir

    return Path(nonebug_path)


@pytest.fixture
def plugin(request, bot):
    plugin = nonebot.load_plugin(request.param)
    assert plugin is not None

    yield plugin

    plugins.pop(plugin.name)
