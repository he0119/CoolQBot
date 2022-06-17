import pytest
from nonebug import App

from tests.fake import fake_group_message_event, fake_private_message_event


@pytest.mark.asyncio
async def test_rank(app: App):
    """测试排行榜"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Bot, Message

    require("src.plugins.repeat")
    from src.plugins.repeat import plugin_config, rank_cmd, recorder_obj

    plugin_config.group_id = [10000]
    recorder_obj._msg_number_list = {10000: {1: {10: 100}}}
    recorder_obj._repeat_list = {10000: {1: {10: 10}}}

    async with app.test_matcher(rank_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event(message=Message("/rank"))

        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10, "no_cache": True},
            result={"card": "test"},
        )
        ctx.should_call_send(
            event, "Love Love Ranking\ntest：10.00%\n\n复读次数排行榜\ntest：10次", True
        )
        ctx.should_finished()


@pytest.mark.asyncio
async def test_rank_limit(app: App):
    """不限制最低次数"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Bot, Message

    require("src.plugins.repeat")
    from src.plugins.repeat import plugin_config, rank_cmd, recorder_obj

    plugin_config.group_id = [10000]
    recorder_obj._msg_number_list = {10000: {1: {10: 100}}}
    recorder_obj._repeat_list = {10000: {1: {10: 10}}}

    async with app.test_matcher(rank_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event(message=Message("/rank n0"))

        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10, "no_cache": True},
            result={"card": "test"},
        )
        ctx.should_call_send(
            event,
            "Love Love Ranking\ntest(100)：10.00%\n\n复读次数排行榜\ntest(100)：10次",
            True,
        )
        ctx.should_finished()


@pytest.mark.asyncio
async def test_rank_private(app: App):
    """私聊获取排行榜"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Bot, Message

    require("src.plugins.repeat")

    from src.plugins.repeat import plugin_config, rank_cmd, recorder_obj

    plugin_config.group_id = [10000]
    recorder_obj._msg_number_list = {10000: {1: {10: 100}}}
    recorder_obj._repeat_list = {10000: {1: {10: 10}}}

    async with app.test_matcher(rank_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_private_message_event(message=Message("/rank"))
        next_event = fake_private_message_event(message=Message("10000"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请问你想查询哪个群？", True)
        ctx.receive_event(bot, next_event)
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10, "no_cache": True},
            result={"card": "test"},
        )
        ctx.should_call_send(
            next_event, "Love Love Ranking\ntest：10.00%\n\n复读次数排行榜\ntest：10次", True
        )
        ctx.should_finished()


@pytest.mark.asyncio
async def test_rank_not_enabled(app: App):
    """没有启用复读的情况"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Bot, Message

    require("src.plugins.repeat")
    from src.plugins.repeat import rank_cmd

    async with app.test_matcher(rank_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event(message=Message("/rank"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "该群未开启复读功能，无法获取排行榜。", True)
        ctx.should_finished()
