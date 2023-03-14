import json
from datetime import date
from pathlib import Path

import pytest
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebug import App
from pytest_mock import MockerFixture
from sqlalchemy import select

from tests.fake import fake_group_message_event_v11


def mocked_get(url: str, **kwargs):
    class MockResponse:
        def __init__(self, json: dict):
            self._json = json

        def json(self):
            return self._json

        @property
        def content(self):
            return json.dumps(self._json).encode("utf-8")

    test_dir = Path(__file__).parent
    if (
        url
        == "https://raw.githubusercontent.com/he0119/CoolQBot/master/src/plugins/morning/holidays.json"
    ):
        with open(test_dir / "holidays.json", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)

    return MockResponse({})


async def test_morning_enabled(app: App):
    """测试每日早安已开启的情况"""
    from nonebot_plugin_datastore import create_session

    from src.plugins.morning.plugins.morning_greeting import (
        MorningGreeting,
        morning_cmd,
    )

    async with create_session() as session:
        session.add(
            MorningGreeting(
                platform="qq",
                bot_id="test",
                group_id="10000",
            )
        )
        await session.commit()

    async with app.test_matcher(morning_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/morning"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "每日早安功能开启中", None)
        ctx.should_finished()


async def test_morning_not_enabled(app: App):
    """测试每日早安关闭的情况"""
    from src.plugins.morning.plugins.morning_greeting import morning_cmd

    async with app.test_matcher(morning_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/morning"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "每日早安功能关闭中", None)
        ctx.should_finished()


async def test_morning_enable(app: App):
    """测试每日早安已，在群里启用的情况"""
    from nonebot_plugin_datastore import create_session

    from src.plugins.morning.plugins.morning_greeting import (
        MorningGreeting,
        morning_cmd,
    )

    async with create_session() as session:
        groups = (await session.scalars(select(MorningGreeting))).all()
        assert len(groups) == 0

    async with app.test_matcher(morning_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/morning 1"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群开启每日早安功能", None)
        ctx.should_finished()

    async with create_session() as session:
        groups = (await session.scalars(select(MorningGreeting))).all()
        assert len(groups) == 1
        assert groups[0].group_id == "10000"


async def test_morning_disable(app: App):
    """测试每日早安，在群里关闭的情况"""
    from nonebot_plugin_datastore import create_session

    from src.plugins.morning.plugins.morning_greeting import (
        MorningGreeting,
        morning_cmd,
    )

    async with create_session() as session:
        session.add(
            MorningGreeting(
                platform="qq",
                bot_id="test",
                group_id="10000",
            )
        )
        await session.commit()

    async with app.test_matcher(morning_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/morning 0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群关闭每日早安功能", None)
        ctx.should_finished()

    async with create_session() as session:
        groups = (await session.scalars(select(MorningGreeting))).all()
        assert len(groups) == 0


async def test_morning_today(app: App, mocker: MockerFixture):
    """测试每日早安，查询今日早安的情况"""
    from src.plugins.morning.plugins.morning_greeting import morning_cmd
    from src.plugins.morning.plugins.morning_greeting.data_source import EXPR_MORNING

    mocked_date = mocker.patch(
        "src.plugins.morning.plugins.morning_greeting.data_source.date"
    )
    mocked_date.today.return_value = date(2022, 1, 1)
    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)
    render_expression = mocker.patch(
        "src.plugins.morning.plugins.morning_greeting.data_source.render_expression"
    )
    render_expression.return_value = Message("test")

    async with app.test_matcher(morning_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/morning today"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message("test"),
            "result",
        )
        ctx.should_finished()

    mocked_date.today.assert_called()
    get.assert_called_once_with(
        "https://raw.githubusercontent.com/he0119/CoolQBot/master/src/plugins/morning/holidays.json"
    )
    render_expression.assert_called_once_with(
        EXPR_MORNING,
        message="今天就是元旦，好好玩吧！",
    )


async def test_morning_push(app: App, mocker: MockerFixture):
    """测试每日早安，发送早安"""
    from nonebot_plugin_datastore import create_session

    from src.plugins.morning.plugins.morning_greeting import MorningGreeting, morning

    get_moring_message = mocker.patch(
        "src.plugins.morning.plugins.morning_greeting.get_moring_message"
    )
    get_moring_message.return_value = Message("test")

    async with create_session() as session:
        session.add(
            MorningGreeting(
                platform="qq",
                bot_id="test",
                group_id="10000",
            )
        )
        await session.commit()

    async with app.test_api() as ctx:
        bot = ctx.create_bot(base=Bot)

        ctx.should_call_api(
            "send_msg",
            {"message_type": "group", "group_id": "10000", "message": Message("test")},
            True,
        )

        await morning()

    get_moring_message.assert_called_once()
