from typing import cast
from unittest.mock import AsyncMock

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event, fake_qqguild_message_event


@pytest.mark.asyncio
async def test_dps_missing_token(app: App):
    """测试 FFLOGS，缺少 Token 的情况"""
    from nonebot import require

    require("src.plugins.ff14")
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.ff14.plugins.fflogs import fflogs_cmd

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/dps me"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "对不起，Token 未设置，无法查询数据。\n请先使用命令\n/dps token <token>\n配置好 Token 后再尝试查询数据。",
            True,
        )
        ctx.should_finished()


@pytest.mark.asyncio
async def test_dps_help(app: App, mocker: MockerFixture):
    """测试 FFLOGS，直接发送 /dps 命令的情况"""
    from nonebot import require

    require("src.plugins.ff14")
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.ff14.plugins.fflogs import (
        __plugin_meta__,
        fflogs_cmd,
        plugin_config,
    )

    plugin_config.fflogs_token = "test"

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/dps"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, f"{__plugin_meta__.name}\n\n{__plugin_meta__.usage}", True
        )
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/dps test"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, f"{__plugin_meta__.name}\n\n{__plugin_meta__.usage}", True
        )
        ctx.should_finished()


@pytest.mark.asyncio
async def test_dps_cache(app: App):
    """测试 FFLOGS，设置缓存的情况"""
    from nonebot import require

    require("src.plugins.ff14")
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.ff14.plugins.fflogs import fflogs_cmd, plugin_config

    plugin_config.fflogs_token = "test"

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/dps cache list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前没有缓存副本。", True)
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/dps cache add p1s"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已添加副本 p1s。", True)
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/dps cache list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前缓存的副本有：\np1s", True)
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/dps cache del p2s"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有缓存 p2s，无法删除。", True)
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/dps cache del p1s"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已删除副本 p1s。", True)
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/dps cache list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前没有缓存副本。", True)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_dps_at_user(app: App, mocker: MockerFixture):
    """测试 FFLOGS，测试 @ 用户的情况"""
    from nonebot import require

    require("src.plugins.ff14")
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from src.plugins.ff14.plugins.fflogs import fflogs, fflogs_cmd, plugin_config

    plugin_config.fflogs_token = "test"
    fflogs.set_character("10000", "name", "server")

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
            message=Message("/dps" + MessageSegment.at(10000))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, MessageSegment.at(10000) + "当前绑定的角色：\n角色：name\n服务器：server", ""
        )
        ctx.should_finished()

    mock = mocker.patch("src.plugins.ff14.plugins.fflogs.get_character_dps_by_user_id")
    mock = cast(AsyncMock, mock)

    async def test(a, b):
        return "test"

    mock.side_effect = test

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
            message=Message("/dps e1s" + MessageSegment.at(10000))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "test", "")
        ctx.should_finished()

    mock.assert_awaited_once_with("e1s", "10000")


@pytest.mark.asyncio
async def test_dps_at_user_qqguild(app: App, mocker: MockerFixture):
    """测试 FFLOGS，测试 @ 用户的情况，QQ频道"""
    from nonebot import require

    require("src.plugins.ff14")
    from nonebot.adapters.qqguild import Message, MessageSegment

    from src.plugins.ff14.plugins.fflogs import fflogs, fflogs_cmd, plugin_config

    plugin_config.fflogs_token = "test"
    fflogs.set_character("10000", "name", "server")

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_qqguild_message_event(
            _message=Message("/dps" + MessageSegment.mention_user(10000))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.mention_user(10000) + "当前绑定的角色：\n角色：name\n服务器：server",
            "",
        )
        ctx.should_finished()

    mock = mocker.patch("src.plugins.ff14.plugins.fflogs.get_character_dps_by_user_id")
    mock = cast(AsyncMock, mock)

    async def test(a, b):
        return "test"

    mock.side_effect = test

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_qqguild_message_event(
            _message=Message("/dps e1s" + MessageSegment.mention_user(10000))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "test", "")
        ctx.should_finished()

    mock.assert_awaited_once_with("e1s", "10000")
