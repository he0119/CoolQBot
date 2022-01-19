import pytest
from nonebug import App

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.repeat",)], indirect=True)
async def test_history(app: App):
    """测试历史"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.repeat import history_cmd, recorder_obj

    recorder_obj._msg_number_list = {10000: {1: {10: 100}}}
    recorder_obj._repeat_list = {10000: {1: {10: 10}}}

    async with app.test_matcher(history_cmd) as ctx:
        bot = ctx.create_bot()

        event = fake_group_message_event(message=Message("/history 2020-1-0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "2020 年 1 月的数据不存在，请换个试试吧 0.0", True)
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.repeat",)], indirect=True)
async def test_history_get_arg(app: App):
    """测试历史"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.repeat import history_cmd, recorder_obj

    recorder_obj._msg_number_list = {10000: {1: {10: 100}}}
    recorder_obj._repeat_list = {10000: {1: {10: 10}}}

    async with app.test_matcher(history_cmd) as ctx:
        bot = ctx.create_bot()

        event = fake_group_message_event(message=Message("/history"))
        year_event = fake_group_message_event(message=Message("2020"))
        month_event = fake_group_message_event(message=Message("1"))
        day_event = fake_group_message_event(message=Message("0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你请输入你要查询的年份", True)

        ctx.receive_event(bot, year_event)
        ctx.should_call_send(year_event, "你请输入你要查询的月份", True)

        ctx.receive_event(bot, month_event)
        ctx.should_call_send(month_event, "你请输入你要查询的日期（如查询整月排名请输入 0）", True)

        ctx.receive_event(bot, day_event)
        ctx.should_call_send(day_event, "2020 年 1 月的数据不存在，请换个试试吧 0.0", True)


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.repeat",)], indirect=True)
async def test_history_get_invalid_arg(app: App):
    """测试历史"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.repeat import history_cmd

    async with app.test_matcher(history_cmd) as ctx:
        bot = ctx.create_bot()

        event = fake_group_message_event(message=Message("/history"))
        year_event = fake_group_message_event(message=Message("2020"))
        invalid_month_event = fake_group_message_event(message=Message("test"))
        month_event = fake_group_message_event(message=Message("1"))
        day_event = fake_group_message_event(message=Message("0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你请输入你要查询的年份", True)

        ctx.receive_event(bot, year_event)
        ctx.should_call_send(year_event, "你请输入你要查询的月份", True)

        ctx.receive_event(bot, invalid_month_event)
        ctx.should_call_send(invalid_month_event, "请只输入数字，不然我没法理解呢！", True)
        ctx.should_rejected()

        ctx.receive_event(bot, month_event)
        ctx.should_call_send(month_event, "你请输入你要查询的日期（如查询整月排名请输入 0）", True)

        ctx.receive_event(bot, day_event)
        ctx.should_call_send(day_event, "2020 年 1 月的数据不存在，请换个试试吧 0.0", True)
