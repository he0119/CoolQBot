""" 自主禁言
"""
from enum import Enum
from typing import Dict

from nonebot import on_command, on_notice
from nonebot.typing import Bot, Event

from src.utils.helpers import render_expression

#region 禁言
EXPR_OK = (
    '好的，满足你！',
    '已禁言。',
    '{duration} 分钟后见~'
) # yapf: disable

EXPR_NEED_HELP = (
    '[CQ:at,qq={user_id}] 你是管理员，我没法禁言你，不过我可以帮你[CQ:at,qq={owner_id}]~',
    '有人想被禁言 {duration} 分钟，群主[CQ:at,qq={owner_id}]，快满足[CQ:at,qq={user_id}]~',
    '群主群主[CQ:at,qq={owner_id}]，快禁言[CQ:at,qq={user_id}] {duration} 分钟'
) # yapf: disable

EXPR_OWNER = (
    '你是群主，你开心就好。',
    '群主别闹了！',
    '没人能禁言你的！请不要再找我了！'
) # yapf: disable


class BanType(Enum):
    """ 禁言的种类 """
    OWNER = '禁言对象是群主'
    NEED_HELP = '需要群主帮忙禁言'
    OK = '可以直接禁言'


def get_ban_type(bot_role: str, sender_role: str) -> BanType:
    """ 计算禁言的种类 """
    if sender_role == 'owner':
        return BanType.OWNER
    if bot_role == 'member':
        return BanType.NEED_HELP
    if bot_role == 'admin' and sender_role == 'admin':
        return BanType.NEED_HELP
    return BanType.OK


ban_cmd = on_command('ban', aliases={'禁言'}, block=True)
ban_cmd.__doc__ = """
ban 禁言

自主禁言

禁言自己，单位为分钟
/ban 30 (禁言 30 分钟)
解除禁言
/ban 0
如果私聊，则在所有支持的群禁言或解除禁言
"""


@ban_cmd.handle()
async def _(bot: Bot, event: Event, state: dict):
    args = str(event.message).strip()

    if not args:
        return

    # 检查输入参数是不是数字
    if args.isdigit():
        state['duration'] = int(args)
    else:
        await ban_cmd.finish('参数必须仅为数字')


@ban_cmd.args_parser
async def _(bot: Bot, event: Event, state: dict):
    args = str(event.message).strip()

    # 检查输入参数是不是数字
    if args.isdigit():
        state[state['_current_key']] = int(args)
    else:
        await ban_cmd.reject('请只输入数字，不然我没法理解呢！')


@ban_cmd.got('duration', prompt='你想被禁言多少分钟呢？')
async def _(bot: Bot, event: Event, state: dict):
    if not _admin_status:
        await refresh_bot_admin_status(bot, event)

    duration = state['duration']
    duration_sec = duration * 60
    user_id = event.user_id
    message_type = event.detail_type

    # 如果在群里发送，则在当前群禁言/解除
    if message_type == 'group':
        group_id = event.group_id
        bot_role = _admin_status[group_id]
        sender_role = event.sender['role']
        ban_type = get_ban_type(bot_role, sender_role)

        if ban_type == BanType.OWNER:
            await ban_cmd.finish(render_expression(EXPR_OWNER), at_sender=True)
        elif ban_type == BanType.NEED_HELP:
            owner_id = await get_owner_id(group_id, bot)
            await ban_cmd.finish(
                render_expression(
                    EXPR_NEED_HELP,
                    duration=duration,
                    owner_id=owner_id,
                    user_id=user_id
                )
            )
        else:
            await bot.set_group_ban(
                group_id=group_id, user_id=user_id, duration=duration_sec
            )
            await ban_cmd.finish(
                render_expression(EXPR_OK, duration=duration), at_sender=True
            )

    # 如果私聊的话，则在所有小誓约支持的群禁言/解除
    elif message_type == 'private':
        for group_id in bot.config.group_id:
            await bot.set_group_ban(
                group_id=group_id, user_id=user_id, duration=duration_sec
            )


async def get_owner_id(group_id: int, bot: Bot) -> int:
    """ 获取群主 QQ 号 """
    group_member_list = await bot.get_group_member_list(group_id=group_id)
    for member in group_member_list:
        if member['role'] == 'owner':
            return member['user_id']


#endregion
#region 机器人是否为管理员
_admin_status: Dict[int, str] = {}


async def refresh_bot_admin_status(bot: Bot, event: Event) -> None:
    """ 更新机器人群内的权限状态 """
    group_list = await bot.get_group_list()
    for group in group_list:
        member_info = await bot.get_group_member_info(
            group_id=group['group_id'], user_id=bot.self_id
        )
        _admin_status[group['group_id']] = member_info['role']


def group_admin(bot: Bot, event: Event, state: dict) -> bool:
    """ 群管理员变动 """
    if event.detail_type == 'group_admin':
        return True
    return False


admin_notice = on_notice(rule=group_admin)


@admin_notice.handle()
async def _(bot: Bot, event: Event, state: dict):
    if bot.self_id == event.self_id:
        if event.sub_type == 'set':
            _admin_status[event.group_id] = 'admin'
        elif event.sub_type == 'unset':
            _admin_status[event.group_id] = 'member'


#endregion
