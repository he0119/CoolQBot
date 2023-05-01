from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_command(app: App):
    """测试机器人收到命令的情况

    什么反应都不会有，直接结束
    """
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.robot")
    from src.plugins.robot import robot_message

    async with app.test_matcher(robot_message) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event_v11(message=Message("test"))

        ctx.receive_event(bot, event)
