import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.repeat",)], indirect=True)
async def test_history(
    app: App,
    mocker: MockerFixture,
):
    """测试历史"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.repeat import history_cmd, recorder_obj

    recorder_obj._msg_number_list = {10000: {1: {10: 100}}}
    recorder_obj._repeat_list = {10000: {1: {10: 10}}}

    async with app.test_matcher(history_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/history 2020-1-0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "2020 年 1 月的数据不存在，请换个试试吧 0.0", "result")
        ctx.should_finished()
