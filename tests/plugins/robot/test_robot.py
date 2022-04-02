import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.robot",)], indirect=True)
async def test_command(app: App):
    """测试机器人收到命令的情况

    什么反应都不会有，直接结束
    """
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.robot import robot_message

    async with app.test_matcher(robot_message) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("test"))

        ctx.receive_event(bot, event)
