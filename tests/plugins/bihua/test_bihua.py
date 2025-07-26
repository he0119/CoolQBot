from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App

from tests.fake import fake_group_message_event_v11

from .utils import FAKE_IMAGE


async def test_bihua(app: App):
    """测试获取壁画"""
    from src.plugins.bihua import bihua_cmd, bihua_service

    await bihua_service.add_bihua(10, "QQClient_10000", "一个名字", FAKE_IMAGE)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/壁画 名字"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message(MessageSegment.image(FAKE_IMAGE)))
        ctx.should_finished(bihua_cmd)


async def test_bihua_get_not_found(app: App):
    """测试获取壁画 - 未找到"""
    from src.plugins.bihua import bihua_cmd, bihua_service

    await bihua_service.add_bihua(10, "QQClient-10000", "一个名字", FAKE_IMAGE)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/壁画 不存在的壁画"), user_id=10, group_id=10000)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "未找到壁画 '不存在的壁画'", True)
        ctx.should_finished(bihua_cmd)
