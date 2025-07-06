"""自主禁言"""

from enum import Enum

from nonebot import on_notice, require
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from nonebot.adapters.onebot.v11.event import GroupAdminNoticeEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna

from src.utils.helpers import render_expression

__plugin_meta__ = PluginMetadata(
    name="自主禁言",
    description="禁言自己或解除自己的禁言",
    usage="""禁言自己，单位为分钟
/ban 30 (禁言 30 分钟)
解除禁言
/ban 0
如果私聊，则需要再提供群号
/ban 0 12345678""",
    supported_adapters={"~onebot.v11"},
)


# region 禁言
EXPR_OK = (
    "好的，满足你！",
    "已禁言。",
    "{duration} 分钟后见~",
)

EXPR_NEED_HELP = (
    "{at_user} 你是管理员，我没法禁言你，不过我可以帮你 {at_owner}~",
    "有人想被禁言 {duration} 分钟，群主 {at_owner}，快满足 {at_user}~",
    "群主群主 {at_owner}，快禁言 {at_user} {duration} 分钟",
)

EXPR_OWNER = (
    "你是群主，你开心就好。",
    "群主别闹了！",
    "没人能禁言你的！请不要再找我了！",
)


class BanType(Enum):
    """禁言的种类"""

    OWNER = "禁言对象是群主"
    NEED_HELP = "需要群主帮忙禁言"
    OK = "可以直接禁言"


def get_ban_type(bot_role: str, sender_role: str) -> BanType:
    """计算禁言的种类"""
    if sender_role == "owner":
        return BanType.OWNER
    if bot_role == "member":
        return BanType.NEED_HELP
    if bot_role == "admin" and sender_role == "admin":
        return BanType.NEED_HELP
    return BanType.OK


ban_cmd = on_alconna(
    Alconna(
        "禁言",
        Args["duration?#时长（分钟）", int],
        Args["group_id?#群号", int],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"ban"},
    use_cmd_start=True,
    block=True,
)


@ban_cmd.handle()
async def ban_handle_first_receive(bot: Bot, duration: Match[int], group_id: Match[int]):
    """获取需要的参数"""
    # 如果没有获取机器人在群中的职位，则获取
    if not _bot_role:
        await refresh_bot_role(bot)

    if duration.available:
        ban_cmd.set_path_arg("duration", duration.result)
    if group_id.available:
        ban_cmd.set_path_arg("group_id", group_id.result)


@ban_cmd.got_path("duration", prompt="你想被禁言多少分钟呢？")
async def ban_handle_group_message(bot: Bot, event: GroupMessageEvent, duration: int):
    """如果在群里发送，则在当前群禁言/解除"""
    group_id = event.group_id
    user_id = event.user_id

    duration_sec = duration * 60

    bot_role = _bot_role[group_id]
    sender_role = event.sender.role
    if not sender_role:
        return

    ban_type = get_ban_type(bot_role, sender_role)
    if ban_type == BanType.OWNER:
        await ban_cmd.finish(render_expression(EXPR_OWNER), at_sender=True)
    elif ban_type == BanType.NEED_HELP:
        owner_id = await get_owner_id(group_id, bot)
        if not owner_id:
            raise Exception("无法获取群主QQ号")
        await ban_cmd.finish(
            render_expression(
                EXPR_NEED_HELP,
                duration=duration,
                at_owner=MessageSegment.at(owner_id),
                at_user=MessageSegment.at(user_id),
            )
        )
    else:
        await bot.set_group_ban(group_id=group_id, user_id=user_id, duration=duration_sec)
        await ban_cmd.finish(render_expression(EXPR_OK, duration=duration), at_sender=True)


@ban_cmd.got_path("duration", prompt="你想被禁言多少分钟呢？")
@ban_cmd.got_path("group_id", prompt="请问你想针对哪个群？")
async def ban_handle_private_message(bot: Bot, event: PrivateMessageEvent, duration: int, group_id: int):
    """如果私聊的话，则向用户请求群号，并仅在支持的群禁言/解除"""
    user_id = event.user_id

    duration_sec = duration * 60

    if group_id not in _bot_role:
        await ban_cmd.finish("抱歉，我不在那个群里，帮不了你 >_<")

    bot_role = _bot_role[group_id]
    sender_role = await get_user_role_in_group(user_id, group_id, bot)

    ban_type = get_ban_type(bot_role, sender_role)
    if ban_type == BanType.OWNER:
        await ban_cmd.finish(render_expression(EXPR_OWNER))
    elif ban_type == BanType.NEED_HELP:
        owner_id = await get_owner_id(group_id, bot)
        if not owner_id:
            raise Exception("无法获取群主QQ号")
        await bot.send_group_msg(
            group_id=group_id,
            message=render_expression(
                EXPR_NEED_HELP,
                duration=duration,
                at_owner=MessageSegment.at(owner_id),
                at_user=MessageSegment.at(user_id),
            ),
        )
        await ban_cmd.finish("帮你@群主了，请耐心等待。")
    else:
        await bot.set_group_ban(group_id=group_id, user_id=user_id, duration=duration_sec)
        await ban_cmd.finish(render_expression(EXPR_OK, duration=duration))


async def get_owner_id(group_id: int, bot: Bot) -> int | None:
    """获取群主 QQ 号"""
    group_member_list = await bot.get_group_member_list(group_id=group_id)
    for member in group_member_list:
        if member["role"] == "owner":
            return member["user_id"]


async def get_user_role_in_group(user_id: int, group_id: int, bot: Bot) -> str:
    """获取用户在群内的身份"""
    group_member_info = await bot.get_group_member_info(user_id=user_id, group_id=group_id)
    return group_member_info["role"]


# endregion
# region 机器人是否为管理员
_bot_role: dict[int, str] = {}


async def refresh_bot_role(bot: Bot) -> None:
    """更新机器人在群内的身份"""
    group_list = await bot.get_group_list()
    for group in group_list:
        member_info = await bot.get_group_member_info(group_id=group["group_id"], user_id=int(bot.self_id))
        _bot_role[group["group_id"]] = member_info["role"]


admin_notice = on_notice()


@admin_notice.handle()
async def admin_handle(bot: Bot, event: GroupAdminNoticeEvent):
    """群内管理员发生变化时，更新机器人在群内的身份"""
    if bot.self_id == str(event.self_id):
        if event.sub_type == "set":
            _bot_role[event.group_id] = "admin"
        elif event.sub_type == "unset":
            _bot_role[event.group_id] = "member"


# endregion
