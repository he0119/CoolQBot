import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.robot",)], indirect=True)
async def test_tencent(
    app: App,
    mocker: MockerFixture,
):
    """测试腾讯闲聊机器人"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.robot import robot_message

    call_tencent_api = mocker.patch("src.plugins.robot.call_tencent_api")
    call_tencent_api.return_value = "test"

    async with app.test_matcher(robot_message) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("你好"), to_me=True)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "test", "result")
        ctx.should_finished()

    call_tencent_api.assert_called_once_with("你好")


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.robot",)], indirect=True)
async def test_tencent_empty_word(
    app: App,
    mocker: MockerFixture,
):
    """测试腾讯闲聊机器人，空字符串"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.robot import robot_message

    call_tencent_api = mocker.patch("src.plugins.robot.call_tencent_api")
    call_tencent_api.return_value = "test"

    async with app.test_matcher(robot_message) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message(), to_me=True)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "test", "result")
        ctx.should_finished()

    call_tencent_api.assert_called_once_with("")