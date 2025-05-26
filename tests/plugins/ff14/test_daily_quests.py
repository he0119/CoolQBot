from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_get_daily_quests(app: App):
    """获取每日委托"""
    from src.plugins.ff14.plugins.ff14_daily_quests import daily_quests_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/每日委托"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你还没有设置每日委托。", True, at_sender=True)
        ctx.should_finished(daily_quests_cmd)


async def test_set_daily_quests(app: App):
    """设置每日委托"""
    from src.plugins.ff14.plugins.ff14_daily_quests import daily_quests_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(
            message=Message("/每日委托 乐园都市笑笑镇，伊弗利特歼灭战, 影之国")
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "与你每日委托相同的群友：\n"
            "乐园都市笑笑镇：无\n"
            "伊弗利特歼灭战：无\n"
            "影之国：无",
            True,
            at_sender=True,
        )
        ctx.should_finished(daily_quests_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/每日委托"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "与你每日委托相同的群友：\n"
            "乐园都市笑笑镇：无\n"
            "伊弗利特歼灭战：无\n"
            "影之国：无",
            True,
            at_sender=True,
        )
        ctx.should_finished(daily_quests_cmd)


async def test_daily_quests_pair(app: App):
    """查询每日委托配对"""
    from src.plugins.ff14.plugins.ff14_daily_quests import daily_quests_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/每日委托"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "你还没有设置每日委托。",
            True,
            at_sender=True,
        )
        ctx.should_finished(daily_quests_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/每日委托 总览"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "今日还没有人设置每日委托。",
            True,
            at_sender=True,
        )
        ctx.should_finished(daily_quests_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(
            message=Message("/每日委托 乐园都市笑笑镇，伊弗利特歼灭战, 神龙歼灭战")
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "与你每日委托相同的群友：\n"
            "乐园都市笑笑镇：无\n"
            "伊弗利特歼灭战：无\n"
            "神龙歼灭战：无",
            True,
            at_sender=True,
        )
        ctx.should_finished(daily_quests_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(
            message=Message("/每日委托 乐园都市笑笑镇，伊弗利特歼灭战, 神龙歼灭战1"),
            user_id=10000,
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "与你每日委托相同的群友：\n"
            "乐园都市笑笑镇：nickname\n"
            "伊弗利特歼灭战：nickname\n"
            "神龙歼灭战1：无",
            True,
            at_sender=True,
        )
        ctx.should_finished(daily_quests_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/每日委托"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "与你每日委托相同的群友：\n乐园都市笑笑镇：nickname10000\n伊弗利特歼灭战：nickname10000\n神龙歼灭战：无",
            True,
            at_sender=True,
        )
        ctx.should_finished(daily_quests_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/每日委托 总览"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "今日所有委托：\n乐园都市笑笑镇：nickname, nickname10000\n伊弗利特歼灭战：nickname, nickname10000\n神龙歼灭战：nickname\n神龙歼灭战1：nickname10000",
            True,
            at_sender=True,
        )
        ctx.should_finished(daily_quests_cmd)
