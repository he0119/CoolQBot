import pytest
from nonebug import App

from tests.fake import fake_private_message_event


@pytest.mark.asyncio
async def test_bind(app: App):
    """测试原神绑定账号"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.genshin")

    from src.plugins.genshin.plugins.bind import bind_cmd

    async with app.test_matcher(bind_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_private_message_event(message=Message("/原神.绑定 cookie"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "绑定成功！", "")
        ctx.should_finished()


@pytest.mark.asyncio
async def test_bind_get_arg(app: App):
    """测试原神绑定账号"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.genshin")

    from src.plugins.genshin.plugins.bind import bind_cmd

    async with app.test_matcher(bind_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_private_message_event(message=Message("/原神.绑定"))
        next_event = fake_private_message_event(message=Message("cookie"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入米游社的 cookie", "")
        ctx.should_rejected()
        ctx.receive_event(bot, next_event)
        ctx.should_call_send(next_event, "绑定成功！", "")
        ctx.should_finished()
