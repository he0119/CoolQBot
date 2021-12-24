from typing import TYPE_CHECKING, Literal, Type

import pytest
from nonebug import App
from pydantic import create_model
from pytest_mock import MockerFixture

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import GroupMessageEvent


def make_fake_event(**fields) -> Type["GroupMessageEvent"]:
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
    from nonebot.adapters.onebot.v11.event import Sender

    _Fake = create_model("_Fake", __base__=GroupMessageEvent, **fields)

    class FakeEvent(_Fake):
        time: int = 1231231
        self_id: int = 1
        post_type: Literal["message"] = "message"
        sub_type: str = "message"
        user_id: int = 1
        message_type: Literal["group"] = "group"
        group_id: int = 10000
        message_id: int = 1
        message: Message = Message("/ban")
        raw_message: str = "/ban"
        font: int = 0
        sender: Sender = Sender(role="member")
        to_me: bool = False

        class Config:
            extra = "forbid"

    return FakeEvent


@pytest.mark.asyncio
async def test_process(app: App, mocker: MockerFixture):
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ban import ban_cmd

    render_expression = mocker.patch("src.plugins.ban.render_expression")
    render_expression.return_value = Message("1 分钟后见~")

    async with app.test_matcher(ban_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = make_fake_event()()
        state = {
            "_prefix": {
                "command": ("ban",),
                "command_arg": Message(),
            }
        }
        next_event = make_fake_event()(message=Message("1"), raw_message="1")

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
            data={"group_id": 10000, "user_id": 1, "duration": 60},
            result=[],
        )
        ctx.should_call_send(next_event, Message("1 分钟后见~"), "result", at_sender=True)
        ctx.should_finished()

    render_expression.assert_called_once()
