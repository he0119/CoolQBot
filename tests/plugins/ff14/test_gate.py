from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


async def test_gete(app: App, mocker: MockerFixture):
    """测试藏宝选门，两个门的情况"""
    from src.plugins.ff14.plugins.ff14_gate import gate_cmd
    from src.plugins.ff14.plugins.ff14_gate.data_source import EXPR_GATE

    render_expression = mocker.patch("src.plugins.ff14.plugins.ff14_gate.data_source.render_expression")
    render_expression.return_value = Message("test")
    randint = mocker.patch("src.plugins.ff14.plugins.ff14_gate.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/gate 2"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message("test"), True, at_sender=True)
        ctx.should_finished(gate_cmd)

    randint.assert_called_once_with(1, 2)
    render_expression.assert_called_once_with(EXPR_GATE, direction="左边")


async def test_gete_ask_arg(app: App, mocker: MockerFixture):
    """测试藏宝选门，两个门的情况"""
    from src.plugins.ff14.plugins.ff14_gate import gate_cmd
    from src.plugins.ff14.plugins.ff14_gate.data_source import EXPR_GATE

    render_expression = mocker.patch("src.plugins.ff14.plugins.ff14_gate.data_source.render_expression")
    render_expression.return_value = Message("test")
    randint = mocker.patch("src.plugins.ff14.plugins.ff14_gate.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/gate"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "总共有多少个门呢？", True)
        ctx.should_rejected(gate_cmd)

        event = fake_group_message_event_v11(message=Message("2"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message("test"), True, at_sender=True)
        ctx.should_finished(gate_cmd)

    randint.assert_called_once_with(1, 2)
    render_expression.assert_called_once_with(EXPR_GATE, direction="左边")


async def test_gete_ask_arg_error(app: App, mocker: MockerFixture):
    """测试藏宝选门，两个门的情况，第一次输入错误"""
    from src.plugins.ff14.plugins.ff14_gate import gate_cmd
    from src.plugins.ff14.plugins.ff14_gate.data_source import EXPR_GATE

    render_expression = mocker.patch("src.plugins.ff14.plugins.ff14_gate.data_source.render_expression")
    render_expression.return_value = Message("test")
    randint = mocker.patch("src.plugins.ff14.plugins.ff14_gate.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/gate"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "总共有多少个门呢？", True)
        ctx.should_rejected(gate_cmd)

        event = fake_group_message_event_v11(message=Message("4"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "暂时只支持两个门或者三个门的情况，请重新输入吧。", True)
        ctx.should_rejected(gate_cmd)

        event = fake_group_message_event_v11(message=Message("2"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message("test"), True, at_sender=True)
        ctx.should_finished(gate_cmd)

    randint.assert_called_once_with(1, 2)
    render_expression.assert_called_once_with(EXPR_GATE, direction="左边")


async def test_gete_ask_arg_whitespace(app: App, mocker: MockerFixture):
    """测试藏宝选门，两个门的情况，有空格"""
    from src.plugins.ff14.plugins.ff14_gate import gate_cmd
    from src.plugins.ff14.plugins.ff14_gate.data_source import EXPR_GATE

    render_expression = mocker.patch("src.plugins.ff14.plugins.ff14_gate.data_source.render_expression")
    render_expression.return_value = Message("test")
    randint = mocker.patch("src.plugins.ff14.plugins.ff14_gate.data_source.randint")
    randint.return_value = 1

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/gate"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "总共有多少个门呢？", True)
        ctx.should_rejected(gate_cmd)

        event = fake_group_message_event_v11(message=Message(" 2 "))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message("test"), True, at_sender=True)
        ctx.should_finished(gate_cmd)

    randint.assert_called_once_with(1, 2)
    render_expression.assert_called_once_with(EXPR_GATE, direction="左边")
