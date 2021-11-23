""" 插件数据 """
from src.utils.plugin import PluginData


def test_ban_plugin(bot):
    data = PluginData("test")

    assert data.exists("test.ini") is False
    assert data.config.get("test", "test") == ""

    data.config.set("test", "test", "test")
    assert data.exists("test.ini")

    assert data.config.get("test", "test") == "test"
