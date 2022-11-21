import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


async def test_gete(app: App, mocker: MockerFixture):
    """测试藏宝选门，两个门的情况"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.ff14")

    from src.plugins.ff14.plugins.gate import gate_cmd
    from src.plugins.ff14.plugins.gate.data_source import EXPR_GATE

    render_expression = mocker.patch(
        "src.plugins.ff14.plugins.gate.data_source.render_expression"
    )
    render_expression.return_value = Message("test")
    randint = mocker.patch("src.plugins.ff14.plugins.gate.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher(gate_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/gate 2"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message("test"), "result", at_sender=True)
        ctx.should_finished()

    randint.assert_called_once_with(1, 2)
    render_expression.assert_called_once_with(EXPR_GATE, direction="左边")


async def test_gete_ask_arg(app: App, mocker: MockerFixture):
    """测试藏宝选门，两个门的情况"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.ff14")

    from src.plugins.ff14.plugins.gate import gate_cmd
    from src.plugins.ff14.plugins.gate.data_source import EXPR_GATE

    render_expression = mocker.patch(
        "src.plugins.ff14.plugins.gate.data_source.render_expression"
    )
    render_expression.return_value = Message("test")
    randint = mocker.patch("src.plugins.ff14.plugins.gate.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher(gate_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/gate"))
        next_event = fake_group_message_event(message=Message("2"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "总共有多少个门呢？", "result")
        ctx.receive_event(bot, next_event)
        ctx.should_call_send(next_event, Message("test"), "result", at_sender=True)
        ctx.should_finished()

    randint.assert_called_once_with(1, 2)
    render_expression.assert_called_once_with(EXPR_GATE, direction="左边")


async def test_gete_ask_arg_error(app: App, mocker: MockerFixture):
    """测试藏宝选门，两个门的情况，第一次输入错误"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.ff14")

    from src.plugins.ff14.plugins.gate import gate_cmd
    from src.plugins.ff14.plugins.gate.data_source import EXPR_GATE

    render_expression = mocker.patch(
        "src.plugins.ff14.plugins.gate.data_source.render_expression"
    )
    render_expression.return_value = Message("test")
    randint = mocker.patch("src.plugins.ff14.plugins.gate.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher(gate_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/gate"))
        next_event = fake_group_message_event(message=Message("4"))
        final_event = fake_group_message_event(message=Message("2"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "总共有多少个门呢？", "result")
        ctx.receive_event(bot, next_event)
        ctx.should_call_send(next_event, "暂时只支持两个门或者三个门的情况，请重新输入吧。", "result")
        ctx.should_rejected()
        ctx.receive_event(bot, final_event)
        ctx.should_call_send(final_event, Message("test"), "result", at_sender=True)
        ctx.should_finished()

    randint.assert_called_once_with(1, 2)
    render_expression.assert_called_once_with(EXPR_GATE, direction="左边")
