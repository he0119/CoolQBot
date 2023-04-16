import json
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock

import httpx
import pytest
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebug import App
from pytest_mock import MockerFixture
from respx import MockRouter
from sqlalchemy import delete

from tests.fake import fake_channel_message_event_v12, fake_group_message_event_v11


@pytest.fixture
async def app(app: App):
    yield app

    # 清理数据库
    from nonebot_plugin_datastore.db import create_session

    from src.plugins.ff14.plugins.ff14_fflogs.models import User

    async with create_session() as session, session.begin():
        await session.execute(delete(User))


@pytest.fixture
async def fflogs_data(app: App) -> dict[str, Any]:
    path = Path(__file__).parent / "fflogs_data.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@pytest.fixture
async def fflogs_character_rankings(app: App) -> dict[str, Any]:
    path = Path(__file__).parent / "fflogs_character_rankings.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


async def test_dps_missing_token(app: App):
    """测试 FFLOGS，缺少 Token 的情况"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs_cmd

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps me"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "对不起，Token 未设置，无法查询数据。\n请先使用命令\n/dps token <token>\n配置好 Token 后再尝试查询数据。",
            True,
        )
        ctx.should_finished()


async def test_dps_help(app: App):
    """测试 FFLOGS，直接发送 /dps 命令的情况"""
    from src.plugins.ff14.plugins.ff14_fflogs import (
        __plugin_meta__,
        fflogs_cmd,
        plugin_data,
    )

    await plugin_data.config.set("token", "test")

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, f"{__plugin_meta__.name}\n\n{__plugin_meta__.usage}", True
        )
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps test"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, f"{__plugin_meta__.name}\n\n{__plugin_meta__.usage}", True
        )
        ctx.should_finished()


async def test_dps_cache(app: App):
    """测试 FFLOGS，设置缓存的情况"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs_cmd, plugin_data

    await plugin_data.config.set("token", "test")

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前没有缓存副本。", True)
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache add p1s"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已添加副本 p1s。", True)
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前缓存的副本有：\np1s", True)
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache del p2s"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有缓存 p2s，无法删除。", True)
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache del p1s"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已删除副本 p1s。", True)
        ctx.should_finished()

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前没有缓存副本。", True)
        ctx.should_finished()


async def test_dps_at_user(
    app: App,
    respx_mock: MockRouter,
    fflogs_data: dict[str, Any],
    fflogs_character_rankings: dict[str, Any],
):
    """测试 FFLOGS，测试 @ 用户的情况"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs, fflogs_cmd, plugin_data

    await plugin_data.config.set("token", "test")
    await fflogs.set_character("qq", "10000", "name", "server")

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/dps" + MessageSegment.at(10000))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, MessageSegment.at(10000) + "当前绑定的角色：\n角色：name\n服务器：server", ""
        )
        ctx.should_finished()

    fflogs_data_mock = respx_mock.get(
        "https://raw.githubusercontent.com/he0119/CoolQBot/master/src/plugins/ff14/fflogs_data.json"
    ).mock(return_value=httpx.Response(200, json=fflogs_data))
    user_dps_mock = respx_mock.get(
        "https://cn.fflogs.com/v1/rankings/character/name/server/CN?zone=29&encounter=65&metric=rdps&api_key=test"
    ).mock(return_value=httpx.Response(200, json=fflogs_character_rankings))

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/dps e1s" + MessageSegment.at(10000))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "伊甸零式希望乐园 觉醒之章1 name-server 的排名(rdps)\n白魔法师(17624/24314) 27.51% 4790.83",
            True,
        )
        ctx.should_finished(fflogs_cmd)

    assert fflogs_data_mock.called
    assert user_dps_mock.called


async def test_dps_at_user_channel(app: App, mocker: MockerFixture):
    """测试 FFLOGS，测试 @ 用户的情况，onebot v12 频道"""
    from nonebot.adapters.onebot.v12 import Bot, Message, MessageSegment

    from src.plugins.ff14.plugins.ff14_fflogs import fflogs, fflogs_cmd, plugin_data

    await plugin_data.config.set("token", "test")
    await fflogs.set_character("qq", "10000", "name", "server")

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot, platform="qq", impl="test")
        event = fake_channel_message_event_v12(
            message=Message("/dps" + MessageSegment.mention("10000"))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.mention("10000") + "当前绑定的角色：\n角色：name\n服务器：server",
            "",
        )
        ctx.should_finished()

    mock = mocker.patch(
        "src.plugins.ff14.plugins.ff14_fflogs.get_character_dps_by_user_id"
    )
    mock = cast(AsyncMock, mock)

    async def test(a, b, c):
        return "test"

    mock.side_effect = test

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot, platform="qq", impl="test")
        event = fake_channel_message_event_v12(
            message=Message("/dps e1s" + MessageSegment.mention("10000"))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "test", "")
        ctx.should_finished()

    mock.assert_awaited_once_with("e1s", "qq", "10000")
