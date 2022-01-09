import pytest
from nonebug import App

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.repeat",)], indirect=True)
async def test_rank(app: App):
    """测试历史"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.repeat import rank_cmd, recorder_obj

    recorder_obj._msg_number_list = {10000: {1: {10: 100}}}
    recorder_obj._repeat_list = {10000: {1: {10: 10}}}

    async with app.test_matcher(rank_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/rank"))

        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10, "no_cache": True},
            result={"card": "test"},
        )
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10, "no_cache": True},
            result={"card": "test"},
        )
        ctx.should_call_send(
            event, "Love Love Ranking\ntest：10.00%\n\n复读次数排行榜\ntest：10次", "result"
        )
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.repeat",)], indirect=True)
async def test_rank_limit(app: App):
    """测试历史"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.repeat import rank_cmd, recorder_obj

    recorder_obj._msg_number_list = {10000: {1: {10: 100}}}
    recorder_obj._repeat_list = {10000: {1: {10: 10}}}

    async with app.test_matcher(rank_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/rank n10"))

        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10, "no_cache": True},
            result={"card": "test"},
        )
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10, "no_cache": True},
            result={"card": "test"},
        )
        ctx.should_call_send(
            event,
            "Love Love Ranking\ntest(100)：10.00%\n\n复读次数排行榜\ntest(100)：10次",
            "result",
        )
        ctx.should_finished()
