import re

from nonebot import CommandSession, permission

from . import cg
from .history import get_history
from .rank import get_rank
from .repeat import is_repeat
from .status import get_status


@cg.command('group')
async def group(session: CommandSession):
    """ 人类本质 """
    message = session.state.get('message')
    if is_repeat(session, message):
        session.finish(message)


@cg.command('sign')
async def sign(session: CommandSession):
    """ 复读打卡（电脑上没法看手机打卡内容） """
    if session.event.group_id in session.bot.config.GROUP_ID:
        title = re.findall(r'title=(\w+\s?\w+)', session.state.get('message'))
        session.finish(f'今天的打卡是 {title[0]}', at_sender=True)


@cg.command(
    'rank',
    aliases=['rank', '排行榜'],
    only_to_me=False,
    permission=permission.GROUP
)
async def rank(session: CommandSession):
    """ 复读排行榜 """
    message = await get_rank(session)
    session.finish(message)


@rank.args_parser
async def _(session: CommandSession):
    stripped_arg = session.current_arg_text.strip()
    if session.is_first_run:
        match = re.match(r'^(?:(\d+))?(?:n(\d+))?$', stripped_arg)
        if match:
            display_number = match.group(1)
            minimal_msg_number = match.group(2)
            display_total_number = False

            if display_number:
                display_number = int(display_number)
            else:
                display_number = 3

            if minimal_msg_number:
                minimal_msg_number = int(minimal_msg_number)
                display_total_number = True
            else:
                minimal_msg_number = 30
            session.state['display_number'] = display_number
            session.state['minimal_msg_number'] = minimal_msg_number
            session.state['display_total_number'] = display_total_number
        return

    if not stripped_arg:
        session.pause('你什么都不输入我怎么知道呢！')

    # 检查输入参数是不是数字
    if stripped_arg.isdigit():
        session.state[session.current_key] = int(stripped_arg)
    else:
        session.pause('请只输入数字，不然我没法理解呢！')


@cg.command(
    'history',
    aliases=['history', '历史'],
    only_to_me=False,
    permission=permission.GROUP
)
async def history(session: CommandSession):
    """ 复读排行榜历史 """
    message = await get_history(session)
    session.finish(message)


@history.args_parser
async def _(session: CommandSession):
    stripped_arg = session.current_arg_text.strip()
    if session.is_first_run:
        match = re.match(r'^(\d+)(?:\-(\d+)(?:\-(\d+))?)?$', stripped_arg)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            if year:
                year = int(year)
            if month:
                month = int(month)
            if day:
                day = int(day)
            session.state['year'] = year
            session.state['month'] = month
            session.state['day'] = day
        return

    if not stripped_arg:
        session.pause('你什么都不输入我怎么知道呢！')

    # 检查输入参数是不是数字
    if stripped_arg.isdigit():
        session.state[session.current_key] = int(stripped_arg)
    else:
        session.pause('请只输入数字，不然我没法理解呢！')


@cg.command(
    'status',
    aliases=['status', '状态'],
    only_to_me=False,
    permission=permission.GROUP
)
async def status(session: CommandSession):
    """ 状态 """
    message = await get_status(session)
    session.finish(message)
