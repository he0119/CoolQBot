""" 自主禁言插件
"""
from nonebot import on_command
from nonebot.typing import Bot, Event

from src.utils.helpers import render_expression

# 定义管理员请求时的「表达（Expression）」
EXPR_ADMIN = (
    '[CQ:at,qq={user_id}] 你是管理员，我没法禁言你，不过我可以帮你[CQ:at,qq={owner_id}]~',
    '有人想被禁言 {duration} 分钟，群主[CQ:at,qq={owner_id}]，快满足[CQ:at,qq={user_id}]~',
    '群主群主[CQ:at,qq={owner_id}]，快禁言[CQ:at,qq={user_id}] {duration} 分钟'
) # yapf: disable

EXPR_OWNER = (
    '你是群主，你开心就好。',
    '群主别闹了！',
    '没人能禁言你的！请不要再找我了！'
) # yapf: disable

ban = on_command('ban', aliases={'禁言'}, priority=1, block=True)
ban.__doc__ = """
ban 禁言

自主禁言

禁言自己，参数为分钟
/ban 30 (禁言 30 分钟)
解除禁言
/ban 0
如果私聊，则在所有注册的群禁言或解除禁言
"""


@ban.handle()
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    if not stripped_arg:
        return

    # 检查输入参数是不是数字
    if stripped_arg.isdigit():
        state['duration'] = int(stripped_arg)
    else:
        await ban.finish('参数必须仅为数字')


@ban.args_parser
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    # 检查输入参数是不是数字
    if stripped_arg.isdigit():
        state['duration'] = int(stripped_arg)
    else:
        await ban.reject('请只输入数字，不然我没法理解呢！')


@ban.got('duration', prompt='你想被禁言多少分钟呢？')
async def _(bot: Bot, event: Event, state: dict):
    duration = state['duration']
    duration_sec = duration * 60
    user_id = event.user_id
    message_type = event.detail_type

    # 如果在群里发送，则在当前群禁言/解除
    if message_type == 'group':
        role = event.sender['role']
        group_id = event.group_id
        if role == 'member':
            await bot.set_group_ban(
                group_id=group_id, user_id=user_id, duration=duration_sec
            )
        elif role == 'admin':
            owner_id = await get_owner(group_id, bot)
            await ban.finish(
                render_expression(
                    EXPR_ADMIN,
                    duration=duration,
                    owner_id=owner_id,
                    user_id=user_id
                )
            )
        elif role == 'owner':
            await ban.finish(render_expression(EXPR_OWNER), at_sender=True)

    # 如果私聊的话，则在所有小誓约支持的群禁言/解除
    elif message_type == 'private':
        for group_id in bot.config.group_id:
            await bot.set_group_ban(
                group_id=group_id, user_id=user_id, duration=duration_sec
            )


async def get_owner(group_id: int, bot: Bot) -> int:
    """ 获取群主 QQ 号
    """
    group_member_list = await bot.get_group_member_list(group_id=group_id)
    for member in group_member_list:
        if member['role'] == 'owner':
            return member['user_id']
