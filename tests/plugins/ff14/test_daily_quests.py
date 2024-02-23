from nonebot.adapters.onebot.v11 import Bot, Message
from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_get_daily_quests(app: App):
    """获取每日委托"""
    from src.plugins.ff14.plugins.ff14_daily_quests import daily_quests_cmd

    async with app.test_matcher(daily_quests_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/每日委托"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你还没有设置每日委托。", True)
        ctx.should_finished(daily_quests_cmd)


async def test_set_daily_quests(app: App):
    """设置每日委托"""
    from src.plugins.ff14.plugins.ff14_daily_quests import daily_quests_cmd

    async with app.test_matcher(daily_quests_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/每日委托 乐园都市笑笑镇，伊弗利特歼灭战, 神龙歼灭战")
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "每日委托设置成功。", True)
        ctx.should_finished(daily_quests_cmd)

    async with app.test_matcher(daily_quests_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/每日委托"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event, "你的每日委托为：乐园都市笑笑镇, 伊弗利特歼灭战, 神龙歼灭战", True
        )
        ctx.should_finished(daily_quests_cmd)


async def test_daily_quests_pair(app: App):
    """查询每日委托配对"""
    from src.plugins.ff14.plugins.ff14_daily_quests import daily_quests_cmd

    async with app.test_matcher(daily_quests_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/每日委托 配对"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "你还没有设置每日委托。",
            True,
        )
        ctx.should_finished(daily_quests_cmd)

    async with app.test_matcher(daily_quests_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/每日委托 乐园都市笑笑镇，伊弗利特歼灭战, 神龙歼灭战")
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "每日委托设置成功。", True)
        ctx.should_finished(daily_quests_cmd)

    async with app.test_matcher(daily_quests_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/每日委托 乐园都市笑笑镇，伊弗利特歼灭战, 神龙歼灭战1"),
            user_id=2,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "每日委托设置成功。", True)
        ctx.should_finished(daily_quests_cmd)

    async with app.test_matcher(daily_quests_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/每日委托 配对"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "与你每日委托相同的群友：\n乐园都市笑笑镇：qq-2\n伊弗利特歼灭战：qq-2\n神龙歼灭战：无",
            True,
        )
        ctx.should_finished(daily_quests_cmd)
