from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_target_weight(app: App):
    """测试设置目标体重"""
    from src.plugins.check_in.plugins.check_in_weight import target_weight_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/目标体重"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入你的目标体重哦～", True)
        ctx.should_rejected(target_weight_cmd)

        event = fake_group_message_event_v11(message=Message("55"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "已成功设置，你真棒哦！祝你早日达成目标～", True, at_sender=True
        )
        ctx.should_finished(target_weight_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/目标体重"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "你的目标体重是 55.0kg，继续努力哦～", True, at_sender=True
        )
        ctx.should_finished(target_weight_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/目标体重 50"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "已成功设置，你真棒哦！祝你早日达成目标～", True, at_sender=True
        )
        ctx.should_finished(target_weight_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/目标体重"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "你的目标体重是 50.0kg，继续努力哦～", True, at_sender=True
        )
        ctx.should_finished(target_weight_cmd)


async def test_weight(app: App):
    """测试记录体重"""
    from src.plugins.check_in.plugins.check_in_weight import weight_record_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/体重打卡 55"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", True, at_sender=True
        )
        ctx.should_finished(weight_record_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/体重打卡"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "今天你的体重是多少呢？", True)
        ctx.should_rejected(weight_record_cmd)

        event = fake_group_message_event_v11(message=Message("55"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", True, at_sender=True
        )
        ctx.should_finished(weight_record_cmd)


async def test_weight_invalid(app: App):
    """测试记录体重不符合标准"""
    from src.plugins.check_in.plugins.check_in_weight import weight_record_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/体重打卡"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "今天你的体重是多少呢？", True)
        ctx.should_rejected(weight_record_cmd)

        event = fake_group_message_event_v11(
            message=Message(MessageSegment.at(123456789))
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "今天你的体重是多少呢？", True)
        ctx.should_rejected(weight_record_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/体重打卡 as"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "体重只能输入数字哦，请重新输入", True, at_sender=True
        )
        ctx.should_rejected(weight_record_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/体重打卡 -1"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "目标体重必须大于 0kg，请重新输入", True, at_sender=True
        )
        ctx.should_rejected(weight_record_cmd)
