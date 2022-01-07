import json
from datetime import date
from pathlib import Path

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


def mocked_get(url: str, **kwargs):
    class MockResponse:
        def __init__(self, json: dict):
            self._json = json

        def json(self):
            return self._json

    test_dir = Path(__file__).parent
    if (
        url
        == "https://cdn.jsdelivr.net/gh/he0119/coolqbot@master/src/plugins/morning/holidays.json"
    ):
        with open(test_dir / "holidays.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)

    return MockResponse({})


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.morning",)], indirect=True)
async def test_morning_enabled(app: App):
    """测试每日早安已开启的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.morning import morning_cmd, plugin_config

    plugin_config.morning_group_id = [10000]

    async with app.test_matcher(morning_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/morning"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "每日早安功能开启中", "result")
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.morning",)], indirect=True)
async def test_morning_not_enabled(app: App):
    """测试每日早安关闭的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.morning import morning_cmd

    async with app.test_matcher(morning_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/morning"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "每日早安功能关闭中", "result")
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.morning",)], indirect=True)
async def test_morning_enable(app: App):
    """测试每日早安已，在群里启用的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.morning import morning_cmd, plugin_config

    assert plugin_config.morning_group_id == []

    async with app.test_matcher(morning_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/morning 1"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群开启每日早安功能", "result")
        ctx.should_finished()

    assert plugin_config.morning_group_id == [10000]


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.morning",)], indirect=True)
async def test_morning_disable(app: App):
    """测试每日早安，在群里关闭的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.morning import morning_cmd, plugin_config

    plugin_config.morning_group_id = [10000]

    assert plugin_config.morning_group_id == [10000]

    async with app.test_matcher(morning_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/morning 0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群关闭每日早安功能", "result")
        ctx.should_finished()

    assert plugin_config.morning_group_id == []


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.morning",)], indirect=True)
async def test_morning_today(
    app: App,
    mocker: MockerFixture,
):
    """测试每日早安，查询今日早安的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.morning import morning_cmd
    from src.plugins.morning.data import EXPR_MORNING

    mocked_date = mocker.patch("src.plugins.morning.data.date")
    mocked_date.today.return_value = date(2022, 1, 1)
    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)
    render_expression = mocker.patch("src.plugins.morning.data.render_expression")
    render_expression.return_value = Message("test")

    async with app.test_matcher(morning_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/morning today"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message("test"),
            "result",
        )
        ctx.should_finished()

    mocked_date.today.assert_called()
    get.assert_called_once_with(
        "https://cdn.jsdelivr.net/gh/he0119/coolqbot@master/src/plugins/morning/holidays.json",
        timeout=30,
    )
    render_expression.assert_called_once_with(
        EXPR_MORNING,
        message="今天就是元旦，好好玩吧！",
    )
