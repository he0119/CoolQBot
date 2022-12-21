from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, PrivateMessageEvent
    from nonebot.adapters.qqguild import MessageEvent


def fake_group_message_event(**field) -> "GroupMessageEvent":
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
    from nonebot.adapters.onebot.v11.event import Sender

    class FakeEvent(GroupMessageEvent):
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
            card="",
            nickname="test",
            role="member",
        )
        to_me: bool = False

        class Config:
            extra = "forbid"

    return FakeEvent(**field)


def fake_private_message_event(**field) -> "PrivateMessageEvent":
    from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent
    from nonebot.adapters.onebot.v11.event import Sender

    class FakeEvent(PrivateMessageEvent):
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

    return FakeEvent(**field)


def fake_qqguild_message_event(**field) -> "MessageEvent":
    from nonebot.adapters.qqguild.api.model import User
    from nonebot.adapters.qqguild.event import MessageCreateEvent

    class FakeEvent(MessageCreateEvent):
        author: User | None = User(id=1)

    return FakeEvent(**field)
