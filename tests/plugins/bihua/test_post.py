from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_bihua_post(app: App):
    """测试搜索壁画 - 无结果"""
    from src.plugins.bihua import post_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        # 使用默认的用户ID 10，它在conftest.py中已经设置好了
        event = fake_group_message_event_v11(message=Message("/搜索壁画 不存在的关键词"), user_id=10, group_id=10000)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "未找到包含 '不存在的关键词' 的壁画", True)
        ctx.should_finished(post_cmd)
