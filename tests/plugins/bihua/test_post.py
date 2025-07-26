from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_bihua_post(app: App):
    """测试壁画发布命令"""
    from src.plugins.bihua import post_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/post 新壁画"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请发送需要收藏的壁画")
        ctx.should_rejected(post_cmd)
