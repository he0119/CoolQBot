from typing import cast

from nonebot.adapters import Bot, Event, Message, MessageSegment
from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent as OneBotV11GroupMessageEvent
from nonebot.adapters.onebot.v11 import Message as OneBotV11Message
from nonebot.adapters.onebot.v12 import Bot as OneBotV12Bot
from nonebot.adapters.onebot.v12 import (
    ChannelMessageEvent as OneBotV12ChannelMessageEvent,
)
from nonebot.adapters.onebot.v12 import GroupMessageEvent as OneBotV12GroupMessageEvent
from nonebot.adapters.onebot.v12 import Message as OneBotV12Message
from nonebot.params import CommandArg

from .models import GroupInfo, MentionedUser, UserInfo


async def get_mentioned_user(args: Message = CommandArg()) -> MentionedUser | None:
    """获取提到的用户信息"""
    if isinstance(args, OneBotV11Message) and (at := args["at"]):
        at = at[0]
        at = cast("MessageSegment", at)
        return MentionedUser(id=at.data["qq"], segment=at)
    if isinstance(args, OneBotV12Message) and (mention := args["mention"]):
        mention = mention[0]
        mention = cast("MessageSegment", mention)
        return MentionedUser(id=mention.data["user_id"], segment=mention)


async def get_platform(bot: Bot) -> str | None:
    """获取平台"""
    if isinstance(bot, OneBotV11Bot):
        return "qq"
    elif isinstance(bot, OneBotV12Bot):
        return bot.platform


async def get_user_info(bot: OneBotV11Bot | OneBotV12Bot, event: Event) -> UserInfo:
    """获取用户信息"""
    if isinstance(bot, OneBotV11Bot):
        platform = "qq"
    else:
        platform = bot.platform

    user_id = str(event.get_user_id())

    return UserInfo(platform=platform, user_id=user_id)


async def get_group_info(
    bot: OneBotV11Bot | OneBotV12Bot,
    event: OneBotV11GroupMessageEvent | OneBotV12GroupMessageEvent | OneBotV12ChannelMessageEvent,
) -> GroupInfo:
    """获取群号或频道号信息"""
    if isinstance(bot, OneBotV11Bot):
        platform = "qq"
    else:
        platform = bot.platform

    group_id = ""
    guild_id = ""
    channel_id = ""
    if isinstance(event, OneBotV11GroupMessageEvent):
        group_id = str(event.group_id)
    elif isinstance(event, OneBotV12GroupMessageEvent):
        group_id = event.group_id
    else:
        guild_id = event.guild_id
        channel_id = event.channel_id

    return GroupInfo(
        platform=platform,
        group_id=group_id,
        channel_id=channel_id,
        guild_id=guild_id,
    )


async def get_plaintext_args(args: Message = CommandArg()) -> str | None:
    """获取纯文本命令参数"""
    if content := args["text"]:
        if message_str := content.extract_plain_text().strip():
            return message_str
