import json
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
        == "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?game_biz=hk4e_cn"
    ):
        with open(test_dir / "game_roles.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)
    if (
        url
        == "https://api-takumi-record.mihoyo.com/game_record/app/genshin/api/dailyNote"
    ):
        with open(test_dir / "daily_note.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)

    return MockResponse({})


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.genshin",)], indirect=True)
async def test_uid(
    app: App,
    mocker: MockerFixture,
):
    """测试原神实时便笺"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.genshin import daily_note_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(daily_note_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/ys.便笺"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "", "")
        ctx.should_finished()
