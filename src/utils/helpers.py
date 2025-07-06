import contextlib
import random
from collections.abc import Sequence
from datetime import timedelta

from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
from nonebot.adapters.onebot.v12 import Bot as OneBotV12Bot
from nonebot.exception import ActionFailed
from nonebot.matcher import Matcher
from nonebot.params import Arg
from nonebot.typing import T_State

from src.utils.permission import SUPERUSER

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

    async def _key_parser(matcher: Matcher, state: T_State, input: int | Message = Arg(key)):
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
    bot: OneBotV11Bot | OneBotV12Bot,
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
                msg = await bot.get_group_member_info(group_id=int(group_id), user_id=int(user_id))
                if msg["card"]:
                    return msg["card"]
                return msg["nickname"]
            except ActionFailed:
                pass
        # 如果不在群里的话(因为有可能会退群)
        msg = await bot.get_stranger_info(user_id=int(user_id))
        return msg["nickname"]
    else:
        if group_id:
            try:
                msg = await bot.get_group_member_info(group_id=group_id, user_id=user_id)
                if msg["user_displayname"]:
                    return msg["user_displayname"]
                return msg["user_name"]
            except ActionFailed:
                pass
        elif channel_id and guild_id:
            try:
                msg = await bot.get_channel_member_info(guild_id=guild_id, channel_id=channel_id, user_id=user_id)
                if msg["user_displayname"]:
                    return msg["user_displayname"]
                return msg["user_name"]
            except ActionFailed:
                pass
        elif guild_id:
            try:
                msg = await bot.get_guild_member_info(guild_id=guild_id, user_id=user_id)
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


def admin_permission():
    permission = SUPERUSER
    with contextlib.suppress(ImportError):
        from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

        permission = permission | GROUP_ADMIN | GROUP_OWNER

    with contextlib.suppress(ImportError):
        from nonebot.adapters.qq.permission import (
            GUILD_ADMIN,
            GUILD_CHANNEL_ADMIN,
            GUILD_OWNER,
        )

        permission = permission | GUILD_ADMIN | GUILD_CHANNEL_ADMIN | GUILD_OWNER

    return permission
