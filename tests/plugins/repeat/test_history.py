from datetime import datetime

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


async def test_history(app: App, mocker: MockerFixture):
    """测试历史"""
    from nonebot import require

    require("src.plugins.repeat")
    from nonebot.adapters.onebot.v11 import Bot, Message

    from src.plugins.repeat import plugin_config, recorder_obj
    from src.plugins.repeat.plugins.history import history_cmd

    mocked_datetime = mocker.patch(
        "src.plugins.repeat.plugins.history.data_source.datetime"
    )
    mocked_datetime.now.return_value = datetime(2020, 1, 2)
    mocked_datetime.return_value = datetime(2020, 1, 1)

    plugin_config.group_id = [10000]
    recorder_obj._msg_number_list = {10000: {1: {10: 100}}}
    recorder_obj._repeat_list = {10000: {1: {10: 10}}}

    async with app.test_matcher(history_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)

        event = fake_group_message_event(message=Message("/history 2020-1-0"))

        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10, "no_cache": True},
            result={"card": "test"},
        )
        ctx.should_call_send(
            event,
            "2020 年 1 月数据\nLove Love Ranking\ntest(100)：10.00%\n\n复读次数排行榜\ntest(100)：10次",
            True,
        )
        ctx.should_finished()

    mocked_datetime.now.assert_called_once()
    mocked_datetime.assert_called_once_with(year=2020, month=1, day=1)


async def test_history_get_arg(app: App, mocker: MockerFixture):
    """请求参数"""
    from nonebot import require

    require("src.plugins.repeat")
    from nonebot.adapters.onebot.v11 import Bot, Message

    from src.plugins.repeat import plugin_config, recorder_obj
    from src.plugins.repeat.plugins.history import history_cmd

    mocked_datetime = mocker.patch(
        "src.plugins.repeat.plugins.history.data_source.datetime"
    )
    mocked_datetime.now.return_value = datetime(2020, 1, 2)
    mocked_datetime.return_value = datetime(2020, 1, 1)

    plugin_config.group_id = [10000]
    recorder_obj._msg_number_list = {10000: {1: {10: 100}}}
    recorder_obj._repeat_list = {10000: {1: {10: 10}}}

    async with app.test_matcher(history_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
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
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10, "no_cache": True},
            result={"card": "test"},
        )
        ctx.should_call_send(
            day_event,
            "2020 年 1 月数据\nLove Love Ranking\ntest(100)：10.00%\n\n复读次数排行榜\ntest(100)：10次",
            True,
        )

    mocked_datetime.now.assert_called_once()
    mocked_datetime.assert_called_once_with(year=2020, month=1, day=1)


async def test_history_get_invalid_args(app: App):
    """参数错误的情况"""
    from nonebot import require

    require("src.plugins.repeat")
    from nonebot.adapters.onebot.v11 import Bot, Message

    from src.plugins.repeat import plugin_config
    from src.plugins.repeat.plugins.history import history_cmd

    plugin_config.group_id = [10000]

    async with app.test_matcher(history_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
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


async def test_history_not_enabled(app: App):
    """没有启用复读的情况"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Bot, Message

    require("src.plugins.repeat")
    from src.plugins.repeat.plugins.history import history_cmd

    async with app.test_matcher(history_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event(message=Message("/history 2020-1-0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "该群未开启复读功能，无法获取历史排行榜。", True)
        ctx.should_finished()
