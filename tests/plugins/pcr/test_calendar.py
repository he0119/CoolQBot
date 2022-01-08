import json
from pathlib import Path

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


def mocked_get(url: str):
    class MockResponse:
        def __init__(self, json: dict):
            self._json = json

        def json(self):
            return self._json

    test_dir = Path(__file__).parent
    if url == "https://pcrbot.github.io/calendar-updater-action/cn.json":
        with open(test_dir / "cn.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)

    return MockResponse({})


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.pcr",)], indirect=True)
async def test_calendar(
    app: App,
    mocker: MockerFixture,
):
    """测试日程"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.pcr import calendar_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(calendar_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/pcr.calendar"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "一周日程：\n======20220108======\n⨠圣迹2.0倍\n⨠活动：狂奔！\u3000兰德索尔公会竞速赛\n⨠神殿2.0倍\n======20220109======\n⨠圣迹2.0倍\n⨠活动：狂奔！\u3000兰德索尔公会竞速赛\n⨠神殿2.0倍\n======20220110======\n⨠圣迹2.0倍\n⨠地下城2.0倍\n⨠活动：狂奔！\u3000兰德索尔公会竞速赛\n⨠神殿2.0倍\n======20220111======\n⨠圣迹2.0倍\n⨠地下城2.0倍\n⨠活动：狂奔！\u3000兰德索尔公会竞速赛\n⨠神殿2.0倍\n======20220112======\n⨠N图2.0倍\n⨠地下城2.0倍\n⨠活动：狂奔！\u3000兰德索尔公会竞速赛\n======20220113======\n⨠N图2.0倍\n⨠地下城2.0倍\n⨠活动：狂奔！\u3000兰德索尔公会竞速赛\n======20220114======\n⨠N图2.0倍\n⨠地下城2.0倍\n⨠探索2.0倍\n⨠活动：新春破晓之星大危机\n⨠活动：狂奔！\u3000兰德索尔公会竞速赛\n\n更多日程：https://pcrbot.github.io/pcr-calendar/#cn",
            "result",
        )
        ctx.should_finished()

    get.assert_called_once_with(
        "https://pcrbot.github.io/calendar-updater-action/cn.json"
    )
