import random
from collections.abc import Sequence
from datetime import timedelta
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
from nonebot.exception import ActionFailed
from nonebot.matcher import Matcher
from nonebot.params import Arg, CommandArg
from nonebot.typing import T_State
from pydantic import BaseModel

from .typing import Expression_T


def render_expression(expr: Expression_T, *args, **kwargs) -> str:
    """Render an expression to message string.

    :param expr: expression to render
    :param args: positional arguments used in str.format()
    :param kwargs: keyword arguments used in str.format()
    :return: the rendered message
    """
    result: str
    if callable(expr):
        result = expr(*args, **kwargs)
    elif isinstance(expr, Sequence) and not isinstance(expr, str):
        result = random.choice(expr)
    else:
        result = expr
    return result.format(*args, **kwargs)


def strtobool(val: str) -> bool:
    """将文本转化成布尔值

    如果是 y, yes, t, true, on, 1, 是, 确认, 开, 返回 True;
    其他的均为返回 False;
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1", "是", "确认", "开"):
        return True
    return False


def parse_int(key: str):
    """解析数字，并将结果存入 state 中"""

    async def _key_parser(
        matcher: Matcher, state: T_State, input: int | Message = Arg(key)
    ):
        if isinstance(input, int):
            return

        plaintext = input.extract_plain_text()
        if not plaintext.isdigit():
            await matcher.reject_arg(key, "请只输入数字，不然我没法理解呢！")
        state[key] = int(plaintext)

    return _key_parser


def parse_bool(key: str):
    """解析布尔值，并将结果存入 state 中"""

    async def _key_parser(state: T_State, input: bool | Message = Arg(key)):
        if isinstance(input, bool):
            return

        plaintext = input.extract_plain_text()
        state[key] = strtobool(plaintext)

    return _key_parser


def parse_str(key: str):
    """解析字符串，并将结果存入 state 中"""

    async def _key_parser(state: T_State, input: str | Message = Arg(key)):
        if isinstance(input, str):
            return

        plaintext = input.extract_plain_text().strip()
        state[key] = plaintext

    return _key_parser


def timedelta_to_chinese(timedelta: timedelta) -> str:
    """将 timedelta 转换为中文时间"""
    days = timedelta.days
    hours = timedelta.seconds // 3600
    minutes = (timedelta.seconds % 3600) // 60
    seconds = timedelta.seconds % 60

    time_str = ""
    if days:
        if days == 1:
            time_str += "明天"
        elif days == 2:
            time_str += "后天"
        else:
            time_str += f"{days}天"
    if hours:
        time_str += f"{hours}小时"
    if minutes:
        time_str += f"{minutes}分钟"
    if seconds:
        time_str += f"{seconds}秒"
    return time_str


async def get_nickname(
    bot: Bot,
    user_id: str,
    group_id: str | None = None,
    guild_id: str | None = None,
    channel_id: str | None = None,
) -> str | None:
    """输入用户 ID，获取用户昵称

    如果提供 group_id，优先获取群名片
    如果提供 guild_id/channel_id，优先获取频道名片
    """
    if isinstance(bot, OneBotV11Bot):
        if group_id:
            try:
                msg = await bot.get_group_member_info(
                    group_id=int(group_id), user_id=int(user_id)
                )
                if msg["card"]:
                    return msg["card"]
                return msg["nickname"]
            except ActionFailed:
                pass
        # 如果不在群里的话(因为有可能会退群)
        msg = await bot.get_stranger_info(user_id=int(user_id))
        return msg["nickname"]
    elif isinstance(bot, OneBotV12Bot):
        if group_id:
            try:
                msg = await bot.get_group_member_info(
                    group_id=group_id, user_id=user_id
                )
                if msg["user_displayname"]:
                    return msg["user_displayname"]
                return msg["user_name"]
            except ActionFailed:
                pass
        elif channel_id and guild_id:
            try:
                msg = await bot.get_channel_member_info(
                    guild_id=guild_id, channel_id=channel_id, user_id=user_id
                )
                if msg["user_displayname"]:
                    return msg["user_displayname"]
                return msg["user_name"]
            except ActionFailed:
                pass
        elif guild_id:
            try:
                msg = await bot.get_guild_member_info(
                    guild_id=guild_id, user_id=user_id
                )
                if msg["user_displayname"]:
                    return msg["user_displayname"]
                return msg["user_name"]
            except ActionFailed:
                pass

        try:
            user = await bot.get_user_info(user_id=user_id)
            if user["user_displayname"]:
                return user["user_displayname"]
            return user["user_name"]
        except ActionFailed:
            pass


class MentionedUser(BaseModel):
    id: str
    segment: MessageSegment


async def get_mentioned_user(args: Message = CommandArg()) -> MentionedUser | None:
    """获取提到的用户信息"""
    if isinstance(args, OneBotV11Message) and (at := args["at"]):
        at = at[0]
        at = cast(MessageSegment, at)
        return MentionedUser(id=at.data["qq"], segment=at)
    if isinstance(args, OneBotV12Message) and (mention := args["mention"]):
        mention = mention[0]
        mention = cast(MessageSegment, mention)
        return MentionedUser(id=mention.data["user_id"], segment=mention)


async def get_platform(bot: Bot) -> str | None:
    """获取平台"""
    if isinstance(bot, OneBotV11Bot):
        return "qq"
    elif isinstance(bot, OneBotV12Bot):
        return bot.platform


class UserInfo(BaseModel, frozen=True):
    """确定一个用户所需的信息"""

    platform: str
    user_id: str


async def get_user_info(bot: OneBotV11Bot | OneBotV12Bot, event: Event) -> UserInfo:
    """获取用户信息"""
    if isinstance(bot, OneBotV11Bot):
        platform = "qq"
    else:
        platform = bot.platform

    user_id = str(event.get_user_id())

    return UserInfo(platform=platform, user_id=user_id)


class GroupInfo(BaseModel, frozen=True):
    """确定一个群或频道所需信息"""

    platform: str
    group_id: str
    guild_id: str
    channel_id: str

    @property
    def detail_type(self) -> str:
        """根据是否有 group_id 判断是群还是频道"""
        if self.group_id:
            return "group"
        return "channel"

    @property
    def send_message_args(self) -> dict[str, str]:
        """发送消息所需数据"""
        return {
            "group_id": self.group_id,
            "channel_id": self.channel_id,
            "guild_id": self.guild_id,
        }


async def get_group_info(
    bot: OneBotV11Bot | OneBotV12Bot,
    event: OneBotV11GroupMessageEvent
    | OneBotV12GroupMessageEvent
    | OneBotV12ChannelMessageEvent,
) -> GroupInfo:
    """获取群号或频道号信息"""
    if isinstance(bot, OneBotV11Bot):
        platform = "qq"
    else:
        platform = bot.platform

    if isinstance(event, OneBotV11GroupMessageEvent):
        group_id = str(event.group_id)
        guild_id = ""
        channel_id = ""
    elif isinstance(event, OneBotV12GroupMessageEvent):
        group_id = event.group_id
        guild_id = ""
        channel_id = ""
    else:
        group_id = ""
        guild_id = event.guild_id
        channel_id = event.channel_id

    return GroupInfo(
        platform=platform,
        group_id=group_id,
        channel_id=channel_id,
        guild_id=guild_id,
    )


async def get_plaintext_content(args: Message = CommandArg()) -> str | None:
    """获取纯文本命令参数"""
    if content := args["text"]:
        if message_str := content.extract_plain_text().strip():
            return message_str
