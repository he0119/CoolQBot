from pathlib import Path

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


def mocked_get(url: str, **kwargs):
    class MockResponse:
        def __init__(self, text: str):
            self.text = text

    test_dir = Path(__file__).parent
    if url == "https://devblogs.microsoft.com/python/feed/":
        with open(test_dir / "feed.xml", "r", encoding="utf-8") as f:
            text = f.read()
        return MockResponse(text)

    return MockResponse("")


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.web.nonebot_bison",)], indirect=True)
async def test_music_get_arg(
    app: App,
    mocker: MockerFixture,
):
    """测试启动问候已开启的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.web.nonebot_bison import add_sub_cmd

    config = get_driver().config
    config.superusers = {"10"}

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(add_sub_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/sub.add"))
        next_event = fake_group_message_event(message=Message("rss"))
        final_event = fake_group_message_event(
            message=Message("https://devblogs.microsoft.com/python/feed/")
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(
                '请输入想要订阅的平台，目前支持：\nbilibili：B站\nrss：RSS\nweibo：新浪微博\n要查看全部平台请输入："全部"'
            ),
            "result",
        )
        ctx.receive_event(bot, next_event)
        ctx.should_call_send(next_event, Message("请输入订阅用户的 ID"), "result")
