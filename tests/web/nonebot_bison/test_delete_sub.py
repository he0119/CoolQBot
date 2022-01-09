import pytest
from nonebug import App

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.web.nonebot_bison",)], indirect=True)
async def test_delete_sub(app: App):
    """测试查询订阅"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.web.nonebot_bison import del_sub_cmd

    config = get_driver().config
    config.superusers = {"10"}

    async with app.test_matcher(del_sub_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/sub.delete"))
        next_event = fake_group_message_event(message=Message("1"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message("订阅的帐号为：\n请输入要删除的订阅的序号"), "result")
        ctx.receive_event(bot, next_event)
        ctx.should_call_send(next_event, "删除错误", "result")
        ctx.should_rejected()
