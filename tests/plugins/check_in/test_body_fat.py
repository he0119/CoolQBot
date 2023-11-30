from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_target_body_fat(app: App):
    """测试设置目标体脂"""
    from src.plugins.check_in.plugins.check_in_body_fat import target_body_fat_cmd

    async with app.test_matcher(target_body_fat_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/目标体脂"))
        event2 = fake_group_message_event_v11(message=Message("55"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入你的目标体脂哦～", True)
        ctx.should_rejected(target_body_fat_cmd)

        ctx.receive_event(bot, event2)
        ctx.should_call_send(
            event2, "已成功设置，你真棒哦！祝你早日达成目标～", True, at_sender=True
        )
        ctx.should_finished(target_body_fat_cmd)

    async with app.test_matcher(target_body_fat_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/目标体脂"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "你的目标体脂是 55.0%，继续努力哦～", True, at_sender=True
        )
        ctx.should_finished(target_body_fat_cmd)

    async with app.test_matcher(target_body_fat_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/目标体脂 50"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "已成功设置，你真棒哦！祝你早日达成目标～", True, at_sender=True
        )
        ctx.should_finished(target_body_fat_cmd)

    async with app.test_matcher(target_body_fat_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/目标体脂"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "你的目标体脂是 50.0%，继续努力哦～", True, at_sender=True
        )
        ctx.should_finished(target_body_fat_cmd)


async def test_body_fat(app: App):
    """测试记录体脂"""
    from src.plugins.check_in.plugins.check_in_body_fat import body_fat_record_cmd

    async with app.test_matcher(body_fat_record_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/体脂打卡 55"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", True, at_sender=True
        )
        ctx.should_finished(body_fat_record_cmd)

    async with app.test_matcher(body_fat_record_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/体脂打卡"))
        event2 = fake_group_message_event_v11(message=Message("55"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "今天你的体脂是多少呢？", True)
        ctx.should_rejected(body_fat_record_cmd)

        ctx.receive_event(bot, event2)
        ctx.should_call_send(
            event2, "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", True, at_sender=True
        )
        ctx.should_finished(body_fat_record_cmd)


async def test_body_fat_invalid(app: App):
    """测试记录体脂不符合标准"""
    from src.plugins.check_in.plugins.check_in_body_fat import body_fat_record_cmd

    async with app.test_matcher(body_fat_record_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/体脂打卡"))
        event2 = fake_group_message_event_v11(
            message=Message(MessageSegment.at(123456789))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "今天你的体脂是多少呢？", True)
        ctx.should_rejected(body_fat_record_cmd)

        ctx.receive_event(bot, event2)
        ctx.should_call_send(event2, "体脂不能为空，请重新输入", True, at_sender=True)
        ctx.should_rejected(body_fat_record_cmd)

    async with app.test_matcher(body_fat_record_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/体脂打卡 as"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "体脂只能输入数字哦，请重新输入", True, at_sender=True
        )
        ctx.should_rejected(body_fat_record_cmd)

    async with app.test_matcher(body_fat_record_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/体脂打卡 -1"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "目标体脂只能在 0% ~ 100% 之间哦，请重新输入", True, at_sender=True
        )
        ctx.should_rejected(body_fat_record_cmd)

    async with app.test_matcher(body_fat_record_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/体脂打卡 101"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "目标体脂只能在 0% ~ 100% 之间哦，请重新输入", True, at_sender=True
        )
        ctx.should_rejected(body_fat_record_cmd)
