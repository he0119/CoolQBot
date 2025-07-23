"""测试壁画插件"""

from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_bihua_search_empty(app: App):
    """测试搜索空结果"""
    from src.plugins.bihua import search_bihua_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/搜索壁画 测试"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "未找到包含 '测试' 的壁画", True)
        ctx.should_finished(search_bihua_cmd)


async def test_bihua_get_not_found(app: App):
    """测试查看不存在的壁画"""
    from src.plugins.bihua import bihua_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/壁画 不存在的壁画"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "未找到壁画 '不存在的壁画'", True)
        ctx.should_finished(bihua_cmd)
