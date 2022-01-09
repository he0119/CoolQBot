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

    async with app.test_matcher(query_sub_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/sub.query"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message("当前无订阅"), "result")
        ctx.should_finished()
