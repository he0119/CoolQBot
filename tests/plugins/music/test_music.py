import json
from pathlib import Path

from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot
from nonebug import App
from pytest_mock import MockerFixture

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
    if url == "http://netease:3000/search?keywords=test":
        with open(test_dir / "netease.json", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)

    return MockResponse({})


async def test_music(app: App, mocker: MockerFixture):
    """测试音乐"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    require("src.plugins.music")
    from src.plugins.music import music_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/music test"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message(MessageSegment.music("163", 1825190456)), None)
        ctx.should_finished(music_cmd)

    get.assert_called_once_with("http://netease:3000/search?keywords=test")


async def test_music_get_arg(
    app: App,
    mocker: MockerFixture,
):
    """测试启动问候已开启的情况"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    require("src.plugins.music")
    from src.plugins.music import music_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/music"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你想听哪首歌呢？", None)
        ctx.should_rejected(music_cmd)

        event = fake_group_message_event_v11(message=Message(MessageSegment.image("12")))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你想听哪首歌呢？", None)
        ctx.should_rejected(music_cmd)

        event = fake_group_message_event_v11(message=Message("test"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message(MessageSegment.music("163", 1825190456)), None)
        ctx.should_finished(music_cmd)

    get.assert_called_once_with("http://netease:3000/search?keywords=test")
