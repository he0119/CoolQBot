import json

import pytest
from nonebug import App

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.web.nonebot_bison",)], indirect=True)
async def test_query_sub(app: App):
    """测试查询订阅"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.web.nonebot_bison import query_sub_cmd
    from src.web.nonebot_bison.config import DATA

    with DATA.open("bison.json", "w", encoding="utf8") as f:
        json.dump(
            {
                "user_target": {
                    "1": {
                        "user": 10000,
                        "user_type": "group",
                        "subs": [
                            {
                                "target": "https://devblogs.microsoft.com/python/feed/",
                                "target_type": "rss",
                                "target_name": "Python",
                                "cats": [],
                                "tags": [],
                            }
                        ],
                    }
                }
            },
            f,
        )

    async with app.test_matcher(query_sub_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/sub.query"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message("订阅的帐号为：\nrss Python https://devblogs.microsoft.com/python/feed/"),
            "result",
        )
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.web.nonebot_bison",)], indirect=True)
async def test_query_sub_empty(app: App):
    """测试查询订阅，订阅为空的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.web.nonebot_bison import query_sub_cmd

    async with app.test_matcher(query_sub_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/sub.query"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message("当前无订阅"), "result")
        ctx.should_finished()
