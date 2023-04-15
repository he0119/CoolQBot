from nonebot.adapters.onebot.v11 import Bot, Message
from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_dietary(app: App):
    """测试记录饮食"""
    from src.plugins.check_in.plugins.check_in_dietary import dietary_cmd

    async with app.test_matcher(dietary_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/饮食打卡 A"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", True, at_sender=True)
        ctx.should_finished(dietary_cmd)

    async with app.test_matcher(dietary_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/饮食打卡 B"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "摸摸你的小肚子，下次不可以再这样了哦～", True, at_sender=True)
        ctx.should_finished(dietary_cmd)

    async with app.test_matcher(dietary_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/饮食打卡 a"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", True, at_sender=True)
        ctx.should_finished(dietary_cmd)

    async with app.test_matcher(dietary_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/饮食打卡"))
        event2 = fake_group_message_event_v11(message=Message("A"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "今天你吃的怎么样呢？请输入 A 或 B（A：健康饮食少油少糖 B：我摆了偷吃了炸鸡奶茶）", True
        )
        ctx.should_rejected(dietary_cmd)

        ctx.receive_event(bot, event2)
        ctx.should_call_send(event2, "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", True, at_sender=True)
        ctx.should_finished(dietary_cmd)


async def test_dietary_invalid(app: App):
    """测试记录饮食不符合标准"""
    from src.plugins.check_in.plugins.check_in_dietary import dietary_cmd

    async with app.test_matcher(dietary_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/饮食打卡 1"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "饮食情况只能输入 A 或 B 哦，请重新输入", True, at_sender=True)
        ctx.should_rejected(dietary_cmd)
