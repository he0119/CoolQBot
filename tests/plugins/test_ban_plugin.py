import typing

import pytest
from nonebot.plugin import Plugin

if typing.TYPE_CHECKING:
    from src.plugins import ban


@pytest.mark.parametrize("plugin", ["src.plugins.ban"], indirect=["plugin"])
def test_ban_plugin(plugin: Plugin):
    assert plugin.name == "src.plugins.ban"
    ban_module: "ban" = plugin.module  # type: ignore
