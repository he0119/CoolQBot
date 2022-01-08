from datetime import datetime

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.repeat",)], indirect=True)
async def test_status(
    app: App,
    mocker: MockerFixture,
):
    """测试状态"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.repeat import recorder_obj, status_cmd

    recorder_obj.start_time = datetime(2020, 1, 1, 0, 0, 0)
    mocked_datetime = mocker.patch("src.plugins.repeat.status.datetime")
    mocked_datetime.now.return_value = datetime(2021, 2, 2, 1, 1, 1)
    mocked_server_status = mocker.patch("src.plugins.repeat.status.server_status")
    mocked_server_status.return_value = "test"

    async with app.test_matcher(status_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/status"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在线 1 年 1 月 1 天 1 小时 1 分钟 1 秒\ntest", "result")
        ctx.should_finished()

    mocked_datetime.now.assert_called_once()
    mocked_server_status.assert_called_once()
