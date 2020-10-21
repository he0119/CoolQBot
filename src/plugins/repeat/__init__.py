""" 复读插件

按照一定条件复读聊天
拥有一些配套功能，如复读排行榜，排行榜历史记录，复读状态
"""
import re

from nonebot import logger, on_command, on_message, scheduler
from nonebot.permission import GROUP
from nonebot.rule import Rule
from nonebot.typing import Bot, Event

from .config import config
from .history import get_history
from .rank import get_rank
from .recorder import recorder
from .repeat_rule import is_repeat
from .status import get_status


#region 自动保存数据
@scheduler.scheduled_job('interval', minutes=1, id='save_recorder')
async def save_recorder():
    """ 每隔一分钟保存一次数据
    """
    # 保存数据前先清理 msg_send_time 列表，仅保留最近 10 分钟的数据
    for group_id in config.group_id:
        recorder.message_number(10, group_id)

    recorder.save_data()


@scheduler.scheduled_job(
    'cron', day=1, hour=0, minute=0, second=0, id='clear_data'
)
async def clear_data():
    """ 每个月最后一天 24 点（下月 0 点）保存记录于历史记录文件夹，并重置记录
    """
    recorder.save_data_to_history()
    recorder.init_data()
    logger.info('记录清除完成')


#endregion
#region 复读
repeat_basic = on_message(
    rule=Rule(is_repeat),
    permission=GROUP,
    priority=5,
    block=True,
)


@repeat_basic.handle()
async def handle_repeat(bot: Bot, event: Event, state: dict):
    await repeat_basic.finish(event.raw_message)


#endregion
#region 运行状态
repeat_status = on_command(
    'status',
    aliases={'状态'},
    priority=5,
    block=True,
)


@repeat_status.handle()
async def handle_status(bot: Bot, event: Event, state: dict):
    await repeat_status.finish(get_status(event.group_id))


#endregion
#region 排行榜
repeat_rank = on_command(
    'rank',
    aliases={'排行榜'},
    priority=1,
    block=True,
)


@repeat_rank.args_parser
async def repeat_rank_args_parser(bot: Bot, event: Event, state: dict):
    """ 排行榜的参数解析函数 """
    args = str(event.message).strip()
    # 检查输入参数是不是数字
    if not args.isdigit():
        await repeat_rank.reject('请只输入数字，不然我没法理解呢！')

    if state['_current_key'] == 'display_number':
        state['display_number'] = int(args)
    if state['_current_key'] == 'minimal_msg_number':
        state['minimal_msg_number'] = int(args)
    if state['_current_key'] == 'display_total_number':
        state['display_total_number'] = int(args)


@repeat_rank.handle()
async def handle_first_rank(bot: Bot, event: Event, state: dict):
    match = re.match(r'^(?:(\d+))?(?:n(\d+))?$', str(event.message).strip())
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
        state['display_number'] = display_number
        state['minimal_msg_number'] = minimal_msg_number
        state['display_total_number'] = display_total_number


@repeat_rank.got('display_number', prompt='请输入想显示的排行条数')
@repeat_rank.got('minimal_msg_number', prompt='请输入进入排行，最少需要发送多少消息')
@repeat_rank.got('display_total_number', prompt='是否显示每个人发送的消息总数')
async def handle_rank(bot: Bot, event: Event, state: dict):
    res = await get_rank(
        display_number=state['display_number'],
        minimal_msg_number=state['minimal_msg_number'],
        display_total_number=state['display_total_number'],
        group_id=event.group_id,
    )
    await repeat_rank.finish(res)


#endregion
#region 历史记录
repeat_history = on_command(
    'history',
    aliases={'历史', '复读历史'},
    priority=1,
    block=True,
)


@repeat_history.args_parser
async def repeat_history_args_parser(bot: Bot, event: Event, state: dict):
    """ 历史记录的参数解析函数 """
    args = str(event.message).strip()
    # 检查输入参数是不是数字
    if not args.isdigit():
        await repeat_history.reject('请只输入数字，不然我没法理解呢！')

    if state['_current_key'] == 'year':
        state['year'] = int(args)
    if state['_current_key'] == 'month':
        state['month'] = int(args)
    if state['_current_key'] == 'day':
        state['day'] = int(args)


@repeat_history.handle()
async def handle_first_history(bot: Bot, event: Event, state: dict):
    match = re.match(
        r'^(\d+)(?:\-(\d+)(?:\-(\d+))?)?$',
        str(event.message).strip()
    )
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
        state['year'] = year
        state['month'] = month
        state['day'] = day


@repeat_history.got('year', prompt='你请输入你要查询的年份')
@repeat_history.got('month', prompt='你请输入你要查询的月份')
@repeat_history.got('day', prompt='你请输入你要查询的日期（如查询整月排名请输入 0）')
async def handle_history(bot: Bot, event: Event, state: dict):
    res = await get_history(
        year=state['year'],
        month=state['month'],
        day=state['day'],
        group_id=event.group_id,
    )
    await repeat_history.finish(res)


#endregion
