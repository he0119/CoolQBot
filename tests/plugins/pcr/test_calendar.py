import json
from datetime import datetime
from pathlib import Path

from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


def mocked_get(url: str):
    class MockResponse:
        def __init__(self, json: dict):
            self._json = json

        def json(self):
            return self._json

    test_dir = Path(__file__).parent
    if url == "https://pcrbot.github.io/calendar-updater-action/cn.json":
        with open(test_dir / "cn.json", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)

    return MockResponse({})


async def test_calendar(app: App, mocker: MockerFixture):
    """测试日程"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.pcr")
    from src.plugins.pcr import calendar_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)
    mocked_datetime = mocker.patch("src.plugins.pcr.data.datetime")
    mocked_datetime.now.return_value = datetime(2022, 1, 8)
    mocked_datetime.strptime = datetime.strptime

    async with app.test_matcher(calendar_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event_v11(message=Message("/公主连结日程表"))

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
    assert mocked_datetime.now.call_count == 2
