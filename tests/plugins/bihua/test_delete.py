from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_bihua_delete_not_found(app: App):
    """测试删除壁画"""
    from src.plugins.bihua import delete_bihua_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        # 使用管理员权限
        event = fake_group_message_event_v11(
            message=Message("/删除壁画 不存在的壁画"), user_id=10, group_id=10000, sender={"role": "admin"}
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "删除失败：壁画不存在", True)
        ctx.should_finished(delete_bihua_cmd)
