import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
async def test_rand(app: App, mocker: MockerFixture):
    """测试点数"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.roll")
    from src.plugins.roll.plugins.rand import rand_cmd

    randint = mocker.patch("src.plugins.roll.plugins.rand.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher(rand_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/rand"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你的点数是 1", "result", at_sender=True)
        ctx.should_finished()

    randint.assert_called_once_with(0, 100)


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.roll",)], indirect=True)
async def test_rand_probability(app: App, mocker: MockerFixture):
    """测试概率"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.roll")
    from src.plugins.roll.plugins.rand import rand_cmd

    randint = mocker.patch("src.plugins.roll.plugins.rand.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher(rand_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/rand 今天是晴天的概率"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "今天是晴天的概率是 1%", "result", at_sender=True)
        ctx.should_finished()

    randint.assert_called_once_with(0, 100)
