from datetime import datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import GroupMessageEvent as GroupMessageEventV11
    from nonebot.adapters.onebot.v11 import (
        PrivateMessageEvent as PrivateMessageEventV11,
    )
    from nonebot.adapters.onebot.v12 import (
        ChannelMessageEvent as ChannelMessageEventV12,
    )
    from nonebot.adapters.onebot.v12 import GroupMessageEvent as GroupMessageEventV12
    from nonebot.adapters.onebot.v12 import (
        PrivateMessageEvent as PrivateMessageEventV12,
    )
    from nonebot.adapters.qq.event import (
        GroupMessageCreateEvent as GroupMessageCreateEventQQ,
    )


def fake_group_message_event_v11(**field) -> "GroupMessageEventV11":
    from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
    from nonebot.adapters.onebot.v11.event import Sender
    from pydantic import create_model

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
            card="",
            nickname="test",
            role="member",
        )
        to_me: bool = False

    return FakeEvent(**field)


def fake_private_message_event_v11(**field) -> "PrivateMessageEventV11":
    from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent
    from nonebot.adapters.onebot.v11.event import Sender
    from pydantic import create_model

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

    return FakeEvent(**field)


def fake_group_message_event_v12(**field) -> "GroupMessageEventV12":
    from nonebot.adapters.onebot.v12 import GroupMessageEvent, Message
    from nonebot.adapters.onebot.v12.event import BotSelf
    from pydantic import create_model

    _Fake = create_model("_Fake", __base__=GroupMessageEvent)

    class FakeEvent(_Fake):
        self: BotSelf = BotSelf(platform="qq", user_id="test")
        id: str = "1"
        time: datetime = datetime.fromtimestamp(1000000)
        type: Literal["message"] = "message"
        detail_type: Literal["group"] = "group"
        sub_type: str = ""
        message_id: str = "10"
        message: Message = Message("test")
        original_message: Message = Message("test")
        alt_message: str = "test"
        user_id: str = "100"
        group_id: str = "10000"
        to_me: bool = False

    return FakeEvent(**field)


def fake_private_message_event_v12(**field) -> "PrivateMessageEventV12":
    from nonebot.adapters.onebot.v12 import Message, PrivateMessageEvent
    from nonebot.adapters.onebot.v12.event import BotSelf
    from pydantic import create_model

    _Fake = create_model("_Fake", __base__=PrivateMessageEvent)

    class FakeEvent(_Fake):
        self: BotSelf = BotSelf(platform="qq", user_id="test")
        id: str = "1"
        time: datetime = datetime.fromtimestamp(1000000)
        type: Literal["message"] = "message"
        detail_type: Literal["private"] = "private"
        sub_type: str = ""
        message_id: str = "10"
        message: Message = Message("test")
        original_message: Message = Message("test")
        alt_message: str = "test"
        user_id: str = "100"
        to_me: bool = False

    return FakeEvent(**field)


def fake_group_message_event_qq(**field) -> "GroupMessageCreateEventQQ":
    from nonebot.adapters.qq.event import GroupMessageCreateEvent
    from nonebot.adapters.qq.models import GroupMemberAuthor
    from pydantic import create_model

    # 处理 author__xxx 形式的嵌套字段
    author_defaults: dict = {
        "id": "10",
        "bot": False,
        "member_openid": "10",
        "username": "test",
    }
    flat_fields: dict = {}
    for key, value in field.items():
        if key.startswith("author__"):
            author_defaults[key.removeprefix("author__")] = value
        else:
            flat_fields[key] = value

    _Fake = create_model("_Fake", __base__=GroupMessageCreateEvent)

    class FakeEvent(_Fake):
        id: str = "1"
        __type__: Literal["GROUP_MESSAGE_CREATE"] = "GROUP_MESSAGE_CREATE"  # type: ignore[assignment]
        to_me: bool = False
        author: GroupMemberAuthor = GroupMemberAuthor(**author_defaults)
        group_id: str = "10000"
        group_openid: str = "10000"
        content: str = "test"
        timestamp: str = "1000000"

    return FakeEvent(**flat_fields)


def fake_channel_message_event_v12(**field) -> "ChannelMessageEventV12":
    from nonebot.adapters.onebot.v12 import ChannelMessageEvent, Message
    from nonebot.adapters.onebot.v12.event import BotSelf
    from pydantic import create_model

    _Fake = create_model("_Fake", __base__=ChannelMessageEvent)

    class FakeEvent(_Fake):
        self: BotSelf = BotSelf(platform="qq", user_id="test")
        id: str = "1"
        time: datetime = datetime.fromtimestamp(1000000)
        type: Literal["message"] = "message"
        detail_type: Literal["channel"] = "channel"
        sub_type: str = ""
        message_id: str = "10"
        message: Message = Message("test")
        original_message: Message = Message("test")
        alt_message: str = "test"
        user_id: str = "10"
        guild_id: str = "10000"
        channel_id: str = "100000"
        to_me: bool = False

    return FakeEvent(**field)
