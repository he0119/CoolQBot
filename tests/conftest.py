from typing import TYPE_CHECKING, Literal, Type

import pytest
from pydantic import create_model

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent


@pytest.fixture()
def fake_group_message_event(request) -> Type["GroupMessageEvent"]:
    param = getattr(request, "param", {})

    from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
    from nonebot.adapters.onebot.v11.event import Sender

    _Fake = create_model("_Fake", __base__=GroupMessageEvent)

    class FakeEvent(_Fake):
        time: int = 1000000
        self_id: int = 1
        post_type: Literal["message"] = "message"
        sub_type: str = "normal"
        user_id: int = 10
        message_type: Literal["group"] = "group"
        group_id: int = 10000
        message_id: int = 1
        message: Message = Message("test")
        raw_message: str = "test"
        font: int = 0
        sender: Sender = Sender(
            card=param.get("card") or "",
            nickname=param.get("nickname") or "test",
            role=param.get("role") or "member",
        )
        to_me: bool = False

        class Config:
            extra = "forbid"

    return FakeEvent


@pytest.fixture()
def fake_private_message_event() -> Type["PrivateMessageEvent"]:
    from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent
    from nonebot.adapters.onebot.v11.event import Sender

    _Fake = create_model("_Fake", __base__=PrivateMessageEvent)

    class FakeEvent(_Fake):
        time: int = 1000000
        self_id: int = 1
        post_type: Literal["message"] = "message"
        sub_type: str = "friend"
        user_id: int = 10
        message_type: Literal["private"] = "private"
        message_id: int = 1
        message: Message = Message("test")
        raw_message: str = "test"
        font: int = 0
        sender: Sender = Sender(nickname="test")
        to_me: bool = False

        class Config:
            extra = "forbid"

    return FakeEvent
