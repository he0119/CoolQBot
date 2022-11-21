import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


async def test_roll(app: App, mocker: MockerFixture):
    """测试点数"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.roll")
    from src.plugins.roll.plugins.nga_roll import roll_cmd

    randint = mocker.patch("src.plugins.roll.plugins.nga_roll.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher(roll_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/roll d100"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "d100=d100(1)=1", "result", at_sender=True)
        ctx.should_finished()

    randint.assert_called_once_with(1, 100)


async def test_roll_get_arg(app: App, mocker: MockerFixture):
    """测试点数，获取参数"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.roll")
    from src.plugins.roll.plugins.nga_roll import roll_cmd

    randint = mocker.patch("src.plugins.roll.plugins.nga_roll.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher(roll_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/roll"))
        next_event = fake_group_message_event(message=Message("d100"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "欢迎使用 NGA 风格 ROLL 点插件\n请问你想怎么 ROLL 点\n你可以输入 d100\n也可以输入 2d100+2d50",
            "result",
        )
        ctx.should_rejected()
        ctx.receive_event(bot, next_event)
        ctx.should_call_send(next_event, "d100=d100(1)=1", "result", at_sender=True)
        ctx.should_finished()

    randint.assert_called_once_with(1, 100)


async def test_roll_invalid(app: App, mocker: MockerFixture):
    """测试点数"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.roll")
    from src.plugins.roll.plugins.nga_roll import roll_cmd

    randint = mocker.patch("src.plugins.roll.plugins.nga_roll.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher(roll_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/roll d100a"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入正确的参数 ~>_<~", "result")
        ctx.should_finished()

    randint.assert_not_called()


async def test_roll_complex(app: App, mocker: MockerFixture):
    """测试点数，复杂点的输入"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.roll")
    from src.plugins.roll.plugins.nga_roll import roll_cmd

    randint = mocker.patch("src.plugins.roll.plugins.nga_roll.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher(roll_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/roll d100+2d50"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "d100+2d50=d100(1)+d50(1)+d50(1)=3",
            "result",
            at_sender=True,
        )
        ctx.should_finished()

    randint.assert_has_calls(
        [
            mocker.call(1, 100),  # type: ignore
            mocker.call(1, 50),
            mocker.call(1, 50),
        ]
    )
