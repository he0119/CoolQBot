from typing import TYPE_CHECKING, Type

import pytest
from nonebug import App
from pytest_mock import MockerFixture

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import GroupMessageEvent


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fake_group_message_event", [{"role": "admin"}, {"role": "member"}], indirect=True
)
@pytest.mark.parametrize("app", [("src.plugins.ban",)], indirect=True)
async def test_ban_group_bot_is_owner(
    app: App,
    mocker: MockerFixture,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试群聊天，直接请求禁言 1 分钟

    机器人为群主，禁言对象为管理员或普通群员（一个群不可能有两个群主）
    """
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ban import EXPR_OK, ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("test")

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
            result={"role": "owner"},
        )
        ctx.should_call_api(
            "set_group_ban",
            data={"group_id": 10000, "user_id": 10, "duration": 60},
            result=[],
        )
        ctx.should_call_send(event, Message("test"), "result", at_sender=True)
        ctx.should_finished()

    render_expression.assert_called_once_with(EXPR_OK, duration=1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fake_group_message_event",
    [{"role": "owner"}, {"role": "admin"}, {"role": "member"}],
    indirect=True,
)
@pytest.mark.parametrize("app", [("src.plugins.ban",)], indirect=True)
async def test_ban_group_bot_is_admin(
    app: App,
    mocker: MockerFixture,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试群聊天，直接请求禁言 1 分钟

    机器人为管理员，禁言对象为群主，管理员或普通群员
    """
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ban import EXPR_NEED_HELP, EXPR_OK, EXPR_OWNER, ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("test")

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
        if event.sender.role == "owner":
            ctx.should_call_send(event, Message("test"), "result", at_sender=True)
        elif event.sender.role == "admin":
            ctx.should_call_api(
                "get_group_member_list",
                data={"group_id": 10000},
                result=[{"role": "owner", "user_id": 100}],
            )
            ctx.should_call_send(event, Message("test"), "result")
        else:
            ctx.should_call_api(
                "set_group_ban",
                data={"group_id": 10000, "user_id": 10, "duration": 60},
                result=[],
            )
            ctx.should_call_send(event, Message("test"), "result", at_sender=True)
        ctx.should_finished()

    if event.sender.role == "admin":
        render_expression.assert_called_once_with(
            EXPR_NEED_HELP,
            duration=1,
            at_owner=MessageSegment.at(100),
            at_user=MessageSegment.at(10),
        )
    elif event.sender.role == "owner":
        render_expression.assert_called_once_with(EXPR_OWNER)
    else:
        render_expression.assert_called_once_with(EXPR_OK, duration=1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fake_group_message_event",
    [{"role": "owner"}, {"role": "admin"}, {"role": "member"}],
    indirect=True,
)
@pytest.mark.parametrize("app", [("src.plugins.ban",)], indirect=True)
async def test_ban_group_bot_is_member(
    app: App,
    mocker: MockerFixture,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试群聊天，直接请求禁言 1 分钟

    机器人为管理员，禁言对象为群主，管理员或普通群员
    """
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ban import EXPR_NEED_HELP, EXPR_OWNER, ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("test")

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
            result={"role": "member"},
        )
        if event.sender.role == "owner":
            ctx.should_call_send(event, Message("test"), "result", at_sender=True)
        else:
            ctx.should_call_api(
                "get_group_member_list",
                data={"group_id": 10000},
                result=[{"role": "owner", "user_id": 100}],
            )
            ctx.should_call_send(event, Message("test"), "result")
        ctx.should_finished()

    if event.sender.role == "owner":
        render_expression.assert_called_once_with(EXPR_OWNER)
    else:
        render_expression.assert_called_once_with(
            EXPR_NEED_HELP,
            duration=1,
            at_owner=MessageSegment.at(100),
            at_user=MessageSegment.at(10),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fake_group_message_event", [{"role": "member"}, {"role": "admin"}], indirect=True
)
@pytest.mark.parametrize("app", [("src.plugins.ban",)], indirect=True)
async def test_ban_group_get_arg(
    app: App,
    mocker: MockerFixture,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试群聊天，获取参数禁言 1 分钟

    机器人为普通群员，禁言对象为管理员或普通群员
    """
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ban import EXPR_OK, ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("test")

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
            result={"role": "owner"},
        )
        ctx.should_call_send(event, "你想被禁言多少分钟呢？", "result")
        ctx.should_rejected()
        ctx.receive_event(bot, next_event, state)
        ctx.should_call_api(
            "set_group_ban",
            data={"group_id": 10000, "user_id": 10, "duration": 60},
            result=[],
        )
        ctx.should_call_send(next_event, Message("test"), "result", at_sender=True)
        ctx.should_finished()

    render_expression.assert_called_once_with(EXPR_OK, duration=1)
