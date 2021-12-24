from typing import TYPE_CHECKING, Type

import pytest
from nonebug import App
from pytest_mock import MockerFixture

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import GroupMessageEvent


@pytest.mark.asyncio
async def test_ban_group(
    app: App,
    mocker: MockerFixture,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试群聊天"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ban import ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("1 分钟后见~")

    async with app.test_matcher(ban_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(
            message=Message("/ban 1"),
            raw_message="/ban 1",
        )
        state = {
            "_prefix": {
                "command": ("ban",),
                "command_arg": Message("1"),
            }
        }

        ctx.receive_event(bot, event, state)
        ctx.should_call_api("get_group_list", data={}, result=[{"group_id": 10000}])
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 1},
            result={"role": "admin"},
        )
        ctx.should_call_api(
            "set_group_ban",
            data={"group_id": 10000, "user_id": 10, "duration": 60},
            result=[],
        )
        ctx.should_call_send(event, Message("1 分钟后见~"), "result", at_sender=True)
        ctx.should_finished()

    render_expression.assert_called_once()


@pytest.mark.asyncio
async def test_ban_group_get_arg(
    app: App,
    mocker: MockerFixture,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试群聊天，并获取参数"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ban import ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("1 分钟后见~")

    async with app.test_matcher(ban_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(
            message=Message("/ban"),
            raw_message="/ban",
        )
        state = {
            "_prefix": {
                "command": ("ban",),
                "command_arg": Message(),
            }
        }
        next_event = fake_group_message_event(message=Message("1"), raw_message="1")

        ctx.receive_event(bot, event, state)
        ctx.should_call_api("get_group_list", data={}, result=[{"group_id": 10000}])
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 1},
            result={"role": "admin"},
        )
        ctx.should_call_send(event, "你想被禁言多少分钟呢？", "result")
        ctx.should_rejected()
        ctx.receive_event(bot, next_event, state)
        ctx.should_call_api(
            "set_group_ban",
            data={"group_id": 10000, "user_id": 10, "duration": 60},
            result=[],
        )
        ctx.should_call_send(next_event, Message("1 分钟后见~"), "result", at_sender=True)
        ctx.should_finished()

    render_expression.assert_called_once()
