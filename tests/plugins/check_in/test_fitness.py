from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_fitness(app: App):
    """测试记录健身"""
    from src.plugins.check_in.plugins.check_in_fitness import fitness_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/健身打卡 测试内容"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", True, at_sender=True)
        ctx.should_finished(fitness_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/健身打卡"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请问你做了什么运动？", True)
        ctx.should_rejected(fitness_cmd)

        even = fake_group_message_event_v11(message=Message("测试内容"))
        ctx.receive_event(bot, even)
        ctx.should_call_send(even, "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", True, at_sender=True)
        ctx.should_finished(fitness_cmd)
