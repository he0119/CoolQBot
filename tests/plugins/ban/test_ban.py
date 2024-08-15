import pytest
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


@pytest.fixture()
async def app(app: App):
    yield app

    from src.plugins.ban import _bot_role

    # 清空机器人角色缓存
    _bot_role.clear()


@pytest.mark.parametrize(
    "sender",
    [
        pytest.param({"role": "admin"}, id="admin"),
        pytest.param({"role": "member"}, id="member"),
    ],
)
async def test_ban_group_bot_is_owner(
    app: App,
    mocker: MockerFixture,
    sender: dict,
):
    """测试群聊天，直接请求禁言 1 分钟

    机器人为群主，禁言对象为管理员或普通群员（一个群不可能有两个群主）
    """
    from src.plugins.ban import EXPR_OK, ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("test")

    async with app.test_matcher(ban_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="1")

        event = fake_group_message_event_v11(message=Message("/ban 1"), sender=sender)
        ctx.receive_event(bot, event)
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
        ctx.should_call_send(event, Message("test"), True, at_sender=True)
        ctx.should_finished(ban_cmd)

    render_expression.assert_called_once_with(EXPR_OK, duration=1)


@pytest.mark.parametrize(
    "sender",
    [
        pytest.param({"role": "owner"}, id="owner"),
        pytest.param({"role": "admin"}, id="admin"),
        pytest.param({"role": "member"}, id="member"),
    ],
)
async def test_ban_group_bot_is_admin(
    app: App,
    mocker: MockerFixture,
    sender: dict,
):
    """测试群聊天，直接请求禁言 1 分钟

    机器人为管理员，禁言对象为群主，管理员或普通群员
    """
    from src.plugins.ban import EXPR_NEED_HELP, EXPR_OK, EXPR_OWNER, ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("test")

    async with app.test_matcher(ban_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="1")

        event = fake_group_message_event_v11(message=Message("/ban 1"), sender=sender)
        ctx.receive_event(bot, event)
        ctx.should_call_api("get_group_list", data={}, result=[{"group_id": 10000}])
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 1},
            result={"role": "admin"},
        )
        if event.sender.role == "owner":
            ctx.should_call_send(event, Message("test"), True, at_sender=True)
        elif event.sender.role == "admin":
            ctx.should_call_api(
                "get_group_member_list",
                data={"group_id": 10000},
                result=[{"role": "owner", "user_id": 100}],
            )
            ctx.should_call_send(event, Message("test"), True)
        else:
            ctx.should_call_api(
                "set_group_ban",
                data={"group_id": 10000, "user_id": 10, "duration": 60},
                result=[],
            )
            ctx.should_call_send(event, Message("test"), True, at_sender=True)
        ctx.should_finished(ban_cmd)

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


@pytest.mark.parametrize(
    "sender",
    [
        pytest.param({"role": "owner"}, id="owner"),
        pytest.param({"role": "admin"}, id="admin"),
        pytest.param({"role": "member"}, id="member"),
    ],
)
async def test_ban_group_bot_is_member(
    app: App,
    mocker: MockerFixture,
    sender: dict,
):
    """测试群聊天，直接请求禁言 1 分钟

    机器人为管理员，禁言对象为群主，管理员或普通群员
    """
    from src.plugins.ban import EXPR_NEED_HELP, EXPR_OWNER, ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("test")

    async with app.test_matcher(ban_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="1")

        event = fake_group_message_event_v11(message=Message("/ban 1"), sender=sender)
        ctx.receive_event(bot, event)
        ctx.should_call_api("get_group_list", data={}, result=[{"group_id": 10000}])
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 1},
            result={"role": "member"},
        )
        if event.sender.role == "owner":
            ctx.should_call_send(event, Message("test"), True, at_sender=True)
        else:
            ctx.should_call_api(
                "get_group_member_list",
                data={"group_id": 10000},
                result=[{"role": "owner", "user_id": 100}],
            )
            ctx.should_call_send(event, Message("test"), True)
        ctx.should_finished(ban_cmd)

    if event.sender.role == "owner":
        render_expression.assert_called_once_with(EXPR_OWNER)
    else:
        render_expression.assert_called_once_with(
            EXPR_NEED_HELP,
            duration=1,
            at_owner=MessageSegment.at(100),
            at_user=MessageSegment.at(10),
        )


@pytest.mark.parametrize(
    "sender",
    [
        pytest.param({"role": "admin"}, id="admin"),
        pytest.param({"role": "member"}, id="member"),
    ],
)
async def test_ban_group_get_arg(
    app: App,
    mocker: MockerFixture,
    sender: dict,
):
    """测试群聊天，获取参数禁言 1 分钟

    机器人为普通群员，禁言对象为管理员或普通群员
    """
    from src.plugins.ban import EXPR_OK, ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("test")

    async with app.test_matcher(ban_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="1")

        event = fake_group_message_event_v11(message=Message("/ban"), sender=sender)
        ctx.receive_event(bot, event)
        ctx.should_call_api("get_group_list", data={}, result=[{"group_id": 10000}])
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 1},
            result={"role": "owner"},
        )
        ctx.should_call_send(event, "你想被禁言多少分钟呢？", True)
        ctx.should_rejected(ban_cmd)

        event = fake_group_message_event_v11(message=Message("1"), sender=sender)
        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "set_group_ban",
            data={"group_id": 10000, "user_id": 10, "duration": 60},
            result=[],
        )
        ctx.should_call_send(event, Message("test"), True, at_sender=True)
        ctx.should_finished(ban_cmd)

    render_expression.assert_called_once_with(EXPR_OK, duration=1)


async def test_ban_group_get_arg_invalid(
    app: App,
    mocker: MockerFixture,
):
    """测试群聊天，获取参数禁言 1 分钟，第一次参数错误"""
    from src.plugins.ban import EXPR_OK, ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("test")
    sender = {"role": "member"}

    async with app.test_matcher(ban_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="1")

        event = fake_group_message_event_v11(message=Message("/ban"), sender=sender)
        ctx.receive_event(bot, event)
        ctx.should_call_api("get_group_list", data={}, result=[{"group_id": 10000}])
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 1},
            result={"role": "owner"},
        )
        ctx.should_call_send(event, "你想被禁言多少分钟呢？", True)
        ctx.should_rejected(ban_cmd)

        event = fake_group_message_event_v11(message=Message("a"), sender=sender)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你想被禁言多少分钟呢？", True)
        ctx.should_rejected(ban_cmd)

        event = fake_group_message_event_v11(message=Message("1"), sender=sender)
        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "set_group_ban",
            data={"group_id": 10000, "user_id": 10, "duration": 60},
            result=[],
        )
        ctx.should_call_send(event, Message("test"), True, at_sender=True)
        ctx.should_finished(ban_cmd)

    render_expression.assert_called_once_with(EXPR_OK, duration=1)
