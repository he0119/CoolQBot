""" 复读插件

按照一定条件复读聊天
拥有一些配套功能，如复读排行榜，排行榜历史记录，复读状态
"""
import re

from nonebot import CommandGroup, on_message, require
from nonebot.adapters.onebot.v11 import Message
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent,
    MessageEvent,
    PrivateMessageEvent,
)
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg, Depends

from src.utils.helpers import check_number, strtobool

from .config import plugin_config
from .history import get_history
from .rank import get_rank
from .recorder import recorder_obj
from .repeat_rule import need_repeat
from .status import get_status

scheduler = require("nonebot_plugin_apscheduler").scheduler

repeat = CommandGroup("repeat")


# region 自动保存数据
@scheduler.scheduled_job("interval", minutes=1, id="save_recorder")
async def save_recorder():
    """每隔一分钟保存一次数据"""
    # 保存数据前先清理 msg_send_time 列表，仅保留最近 10 分钟的数据
    for group_id in plugin_config.group_id:
        recorder_obj.message_number(10, group_id)

    recorder_obj.save_data()


@scheduler.scheduled_job("cron", day=1, hour=0, minute=0, second=0, id="clear_recorder")
async def clear_recorder():
    """每个月最后一天 24 点（下月 0 点）保存记录于历史记录文件夹，并重置记录"""
    recorder_obj.save_data_to_history()
    recorder_obj.init_data()
    logger.info("记录清除完成")


# endregion
# region 复读
repeat_message = on_message(
    rule=need_repeat,
    permission=GROUP,
    priority=5,
    block=True,
)


@repeat_message.handle()
async def repeat_message_handle(event: GroupMessageEvent):
    await repeat_message.finish(event.message)


repeat_cmd = repeat.command("basic", aliases={"repeat", "复读"}, permission=GROUP)
repeat_cmd.__doc__ = """
复读

查看当前群是否启用复读功能
/repeat
启用复读功能
/repeat on
关闭复读功能
/repeat off
"""


@repeat_cmd.handle()
async def repeat_handle(event: GroupMessageEvent, arg: Message = CommandArg()):
    args = arg.extract_plain_text()

    group_id = event.group_id

    if args and group_id:
        if strtobool(args):
            plugin_config.group_id += [group_id]
            recorder_obj.add_new_group()
            await repeat_cmd.finish("已在本群开启复读功能")
        else:
            plugin_config.group_id = [
                n for n in plugin_config.group_id if n != group_id
            ]
            await repeat_cmd.finish("已在本群关闭复读功能")
    else:
        if group_id in plugin_config.group_id:
            await repeat_cmd.finish("复读功能开启中")
        else:
            await repeat_cmd.finish("复读功能关闭中")


# endregion
# region 运行状态
status_cmd = repeat.command("status", aliases={"status", "状态"})
status_cmd.__doc__ = """
状态

获取当前的机器人状态
/status
"""


@status_cmd.handle()
async def status_handle(event: MessageEvent):
    group_id = event.group_id if isinstance(event, GroupMessageEvent) else None
    message = get_status(group_id)
    await status_cmd.finish(message)


# endregion
# region 排行榜
rank_cmd = repeat.command("rank", aliases={"rank", "排行榜"})
rank_cmd.__doc__ = """
排行榜

获取当前的排行榜（默认显示前三名）
/rank
限制进入排行榜所需发送消息的数量
/rank n30
限制显示的人数
/rank 3n30
"""


async def get_display_number(
    matcher: Matcher, display_number: str = ArgPlainText()
) -> int:
    await check_number(display_number, matcher)
    return int(display_number)


async def get_minimal_msg_number(
    matcher: Matcher, minimal_msg_number: str = ArgPlainText()
) -> int:
    await check_number(minimal_msg_number, matcher)
    return int(minimal_msg_number)


async def get_display_total_number(display_total_number: str = ArgPlainText()) -> bool:
    return strtobool(display_total_number)


async def get_group_id(matcher: Matcher, group_id: str = ArgPlainText()) -> int:
    await check_number(group_id, matcher)
    return int(group_id)


@rank_cmd.handle()
async def rank_handle_first_receive(matcher: Matcher, arg: Message = CommandArg()):
    match = re.match(r"^(?:(\d+))?(?:n(\d+))?$", arg.extract_plain_text())
    if match:
        display_number = match.group(1)
        minimal_msg_number = match.group(2)
        display_total_number = "False"

        if display_number:
            display_number = display_number
        else:
            display_number = "3"

        if minimal_msg_number:
            minimal_msg_number = minimal_msg_number
            display_total_number = "True"
        else:
            minimal_msg_number = "30"

        matcher.set_arg("display_number", Message(display_number))
        matcher.set_arg("minimal_msg_number", Message(minimal_msg_number))
        matcher.set_arg("display_total_number", Message(display_total_number))


@rank_cmd.got("display_number", prompt="请输入想显示的排行条数")
@rank_cmd.got("minimal_msg_number", prompt="请输入进入排行，最少需要发送多少消息")
@rank_cmd.got("display_total_number", prompt="是否显示每个人发送的消息总数")
async def rank_handle_group_message(
    bot: Bot,
    event: GroupMessageEvent,
    display_number: int = Depends(get_display_number),
    minimal_msg_number: int = Depends(get_minimal_msg_number),
    display_total_number: bool = Depends(get_display_total_number),
):
    res = await get_rank(
        bot,
        display_number=display_number,
        minimal_msg_number=minimal_msg_number,
        display_total_number=display_total_number,
        group_id=event.group_id,
    )
    await rank_cmd.finish(res)


@rank_cmd.got("display_number", prompt="请输入想显示的排行条数")
@rank_cmd.got("minimal_msg_number", prompt="请输入进入排行，最少需要发送多少消息")
@rank_cmd.got("display_total_number", prompt="是否显示每个人发送的消息总数")
@rank_cmd.got("group_id", prompt="请问你想查询哪个群？")
async def rank_handle_private_message(
    bot: Bot,
    event: PrivateMessageEvent,
    display_number: int = Depends(get_display_number),
    minimal_msg_number: int = Depends(get_minimal_msg_number),
    display_total_number: bool = Depends(get_display_total_number),
    group_id: int = Depends(get_group_id),
):
    res = await get_rank(
        bot,
        display_number=display_number,
        minimal_msg_number=minimal_msg_number,
        display_total_number=display_total_number,
        group_id=group_id,
    )
    await rank_cmd.finish(res)


# endregion
# region 历史记录
history_cmd = repeat.command("history", aliases={"history", "历史", "复读历史"})
history_cmd.__doc__ = """
历史

显示2020年1月的数据
/history 2020-1
显示2020年1月1日的数据
/history 2020-1-1
"""


async def get_year(matcher: Matcher, year: str = ArgPlainText()) -> int:
    await check_number(year, matcher)
    return int(year)


async def get_month(matcher: Matcher, month: str = ArgPlainText()) -> int:
    await check_number(month, matcher)
    return int(month)


async def get_day(matcher: Matcher, day: str = ArgPlainText()) -> int:
    await check_number(day, matcher)
    return int(day)


@history_cmd.handle()
async def history_handle_first_receive(matcher: Matcher, arg: Message = CommandArg()):
    match = re.match(r"^(\d+)(?:\-(\d+)(?:\-(\d+))?)?$", arg.extract_plain_text())
    if match:
        year = match.group(1)
        month = match.group(2)
        day = match.group(3)
        if year:
            matcher.set_arg("year", Message(year))
        if month:
            matcher.set_arg("month", Message(month))
        if day:
            matcher.set_arg("day", Message(day))


@history_cmd.got("year", prompt="你请输入你要查询的年份")
@history_cmd.got("month", prompt="你请输入你要查询的月份")
@history_cmd.got("day", prompt="你请输入你要查询的日期（如查询整月排名请输入 0）")
async def history_handle_group_message(
    event: GroupMessageEvent,
    year: int = Depends(get_year),
    month: int = Depends(get_month),
    day: int = Depends(get_day),
):
    res = await get_history(
        year=year,
        month=month,
        day=day,
        group_id=event.group_id,
    )
    await history_cmd.finish(res)


@history_cmd.got("year", prompt="你请输入你要查询的年份")
@history_cmd.got("month", prompt="你请输入你要查询的月份")
@history_cmd.got("day", prompt="你请输入你要查询的日期（如查询整月排名请输入 0）")
@history_cmd.got("group_id", prompt="请问你想查询哪个群？")
async def history_handle_private_message(
    event: PrivateMessageEvent,
    year: int = Depends(get_year),
    month: int = Depends(get_month),
    day: int = Depends(get_day),
    group_id: int = Depends(get_group_id),
):
    res = await get_history(
        year=year,
        month=month,
        day=day,
        group_id=group_id,
    )
    await history_cmd.finish(res)


# endregion
