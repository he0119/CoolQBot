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

    if url == "https://api.bilibili.com/x/space/acc/info":
        with open(test_dir / "bilibili_info.json", "r", encoding="utf-8") as f:
            text = f.read()
        return MockResponse(text)

    return MockResponse("")


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.web.nonebot_bison",)], indirect=True)
async def test_add_sub_rss(
    app: App,
    mocker: MockerFixture,
):
    """测试添加订阅，添加 RSS"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
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
            "",
        )
        ctx.receive_event(bot, next_event)
        ctx.should_call_send(next_event, Message("请输入订阅用户的 ID"), "")
        ctx.receive_event(bot, final_event)
        ctx.should_call_send(final_event, "添加 Python 成功", "")

    get.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.web.nonebot_bison",)], indirect=True)
async def test_add_sub_bilibili(
    app: App,
    mocker: MockerFixture,
):
    """测试添加订阅，添加 Bilibili"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.web.nonebot_bison import add_sub_cmd

    config = get_driver().config
    config.superusers = {"10"}

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(add_sub_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/sub.add"))
        platform_event = fake_group_message_event(message=Message("bilibili"))
        id_event = fake_group_message_event(message=Message("4549624"))
        cats_event = fake_group_message_event(message=Message("一般动态,视频,纯文字,转发"))
        tags_event = fake_group_message_event(message=Message("全部标签"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(
                '请输入想要订阅的平台，目前支持：\nbilibili：B站\nrss：RSS\nweibo：新浪微博\n要查看全部平台请输入："全部"'
            ),
            "",
        )
        ctx.receive_event(bot, platform_event)
        ctx.should_call_send(platform_event, Message("请输入订阅用户的 ID"), "")
        ctx.receive_event(bot, id_event)
        ctx.should_call_send(
            id_event, Message("请输入要订阅的类别，以逗号分隔，支持的类别有：一般动态，专栏文章，视频，纯文字，转发"), ""
        )
        ctx.receive_event(bot, cats_event)
        ctx.should_call_send(cats_event, Message('请输入要订阅的标签，以逗号分隔，订阅所有标签输入"全部标签"'), "")
        ctx.receive_event(bot, tags_event)
        ctx.should_call_send(tags_event, "添加 Liyuu_ 成功", "")
        ctx.should_finished()

    get.assert_called_once()
