from typing import TYPE_CHECKING, Type

import pytest
from nonebug import App
from pytest_mock import MockerFixture

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import GroupMessageEvent


@pytest.mark.asyncio
@pytest.mark.parametrize("data_path", ["src.plugin.ff14"], indirect=True)
async def test_gete(
    app: App,
    data_path,
    mocker: MockerFixture,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试藏宝选门，两个门的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ff14 import gate_cmd
    from src.plugins.ff14.gate import EXPR_GATE

    render_expression = mocker.patch("src.plugins.ff14.gate.render_expression")
    render_expression.return_value = Message("test")
    randint = mocker.patch("src.plugins.ff14.gate.randint")
    randint.return_value = 1

    async with app.test_matcher(gate_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(
            message=Message("/gate 2"),
            raw_message="/gate 2",
        )
        state = {
            "_prefix": {
                "command": ("gate",),
                "command_arg": Message("2"),
            }
        }

        ctx.receive_event(bot, event, state)
        ctx.should_call_send(event, Message("test"), "result", at_sender=True)
        ctx.should_finished()

    randint.assert_called_once_with(1, 2)
    render_expression.assert_called_once_with(EXPR_GATE, direction="左边")


@pytest.mark.asyncio
@pytest.mark.parametrize("data_path", ["src.plugin.ff14"], indirect=True)
async def test_gete_ask_arg(
    app: App,
    data_path,
    mocker: MockerFixture,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试藏宝选门，两个门的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ff14 import gate_cmd
    from src.plugins.ff14.gate import EXPR_GATE

    render_expression = mocker.patch("src.plugins.ff14.gate.render_expression")
    render_expression.return_value = Message("test")
    randint = mocker.patch("src.plugins.ff14.gate.randint")
    randint.return_value = 1

    async with app.test_matcher(gate_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(
            message=Message("/gate"),
            raw_message="/gate",
        )
        state = {
            "_prefix": {
                "command": ("gate",),
                "command_arg": Message(),
            }
        }
        next_event = fake_group_message_event(
            message=Message("2"),
            raw_message="2",
        )

        ctx.receive_event(bot, event, state)
        ctx.should_call_send(event, "总共有多少个门呢？", "result")
        ctx.receive_event(bot, next_event, state)
        ctx.should_call_send(next_event, Message("test"), "result", at_sender=True)
        ctx.should_finished()

    randint.assert_called_once_with(1, 2)
    render_expression.assert_called_once_with(EXPR_GATE, direction="左边")
