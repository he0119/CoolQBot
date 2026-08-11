import json
from datetime import date
from pathlib import Path

import httpx
import respx
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from nonebug_saa import should_send_saa
from pytest_mock import MockerFixture
from sqlalchemy import select

from tests.fake import fake_group_message_event_v11


async def test_morning_enabled(app: App):
    """测试每日早安已开启的情况"""
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_saa import TargetQQGroup

    from src.plugins.morning.plugins.morning_greeting import (
        MorningGreeting,
        morning_cmd,
    )

    async with get_session() as session:
        session.add(MorningGreeting(target=TargetQQGroup(group_id=10000).model_dump()))
        await session.commit()

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/morning"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "每日早安功能开启中", None)
        ctx.should_finished(morning_cmd)


async def test_morning_disabled(app: App):
    """测试每日早安关闭的情况"""
    from src.plugins.morning.plugins.morning_greeting import morning_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/morning"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "每日早安功能关闭中", None)
        ctx.should_finished(morning_cmd)


async def test_morning_enable(app: App):
    """测试每日早安已，在群里启用的情况"""
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_saa import TargetQQGroup

    from src.plugins.morning.plugins.morning_greeting import (
        MorningGreeting,
        morning_cmd,
    )

    async with get_session() as session:
        groups = (await session.scalars(select(MorningGreeting))).all()
        assert len(groups) == 0

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/morning 1"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群开启每日早安功能", None)
        ctx.should_finished(morning_cmd)

    async with get_session() as session:
        groups = (await session.scalars(select(MorningGreeting))).all()
        assert len(groups) == 1
        assert groups[0].saa_target == TargetQQGroup(group_id=10000)


async def test_morning_disable(app: App):
    """测试每日早安，在群里关闭的情况"""
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_saa import TargetQQGroup

    from src.plugins.morning.plugins.morning_greeting import (
        MorningGreeting,
        morning_cmd,
    )

    async with get_session() as session:
        session.add(MorningGreeting(target=TargetQQGroup(group_id=10000).model_dump()))
        await session.commit()

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/morning 0"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群关闭每日早安功能", None)
        ctx.should_finished(morning_cmd)

    async with get_session() as session:
        groups = (await session.scalars(select(MorningGreeting))).all()
        assert len(groups) == 0


@respx.mock
async def test_morning_today(app: App, mocker: MockerFixture):
    """测试每日早安，查询今日早安的情况"""
    import nonebot_plugin_localstore as store

    from src.plugins.morning.plugins.morning_greeting import morning_cmd
    from src.plugins.morning.plugins.morning_greeting.data_source import EXPR_MORNING, HOLIDAYS_DATA

    mocked_date = mocker.patch("src.plugins.morning.plugins.morning_greeting.data_source.date")
    mocked_date.today.return_value = date(2022, 1, 1)
    HOLIDAYS_DATA.clear_memory_cache()
    data = json.loads((Path(__file__).parent / "holidays.json").read_text(encoding="utf-8"))
    request = respx.get("https://bot-docs.hehome.xyz/holidays.json").mock(return_value=httpx.Response(200, json=data))
    render_expression = mocker.patch("src.plugins.morning.plugins.morning_greeting.data_source.render_expression")
    render_expression.return_value = Message("test")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/morning today"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message("test"),
            "result",
        )
        ctx.should_finished(morning_cmd)

    mocked_date.today.assert_called()
    assert request.call_count == 1
    assert HOLIDAYS_DATA.cache_file == store.BASE_CACHE_DIR / "morning" / "morning_greeting" / "holidays.json"
    render_expression.assert_called_once_with(
        EXPR_MORNING,
        message="今天就是元旦，好好玩吧！",
    )


async def test_morning_update_failure(app: App, mocker: MockerFixture):
    from src.plugins.morning.plugins.morning_greeting import HOLIDAYS_DATA, morning_cmd
    from src.utils.remote_data import RemoteDataError

    mocker.patch.object(HOLIDAYS_DATA, "update", side_effect=RemoteDataError("unavailable"))

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/morning update"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "节假日数据更新失败，已保留原缓存", "result")
        ctx.should_finished(morning_cmd)


async def test_morning_push(app: App, mocker: MockerFixture):
    """测试每日早安，发送早安"""
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_saa import MessageFactory, TargetQQGroup, Text

    from src.plugins.morning.plugins.morning_greeting import MorningGreeting, morning

    get_moring_message = mocker.patch("src.plugins.morning.plugins.morning_greeting.get_moring_message")
    get_moring_message.return_value = Message("test")

    text = Text("test")
    mock_text = mocker.patch("src.plugins.morning.plugins.morning_greeting.Text")
    mock_text.return_value = text

    target = TargetQQGroup(group_id=10000)
    async with get_session() as session:
        session.add(MorningGreeting(target=target.model_dump()))
        await session.commit()

    async with app.test_api() as ctx:
        bot = ctx.create_bot(base=Bot)

        should_send_saa(ctx, MessageFactory(text), bot, target=target)

        await morning()

    get_moring_message.assert_called_once()
    mock_text.assert_called_once()
