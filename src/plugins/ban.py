""" 自主禁言插件
"""
from nonebot import CommandSession, on_command
from .tools import to_number


@on_command('ban', aliases=('禁言'), only_to_me=False)
async def ban(session: CommandSession):
    duration = session.get('duration', prompt='你想被禁言多少分钟呢？')

    duration = duration * 60

    await session.bot.set_group_ban(group_id=session.bot.config.GROUP_ID,
                                    user_id=session.ctx['sender']['user_id'],
                                    duration=duration)


@ban.args_parser
async def _(session: CommandSession):
    # 去掉消息首尾的空白符
    stripped_arg = session.current_arg_text.strip()

    if session.is_first_run:
        # 该命令第一次运行（第一次进入命令会话）
        if stripped_arg:
            session.state['duration'] = to_number(stripped_arg, session)
        return

    if not stripped_arg:
        session.pause('禁言时间不能为空呢，请重新输入')

    session.state[session.current_key] = to_number(stripped_arg, session)
