"""历史记录"""

import re

from nonebot.adapters import Bot, Message
from nonebot.params import Arg, CommandArg, Depends
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from src.plugins.repeat import repeat
from src.utils.annotated import GroupInfo
from src.utils.helpers import parse_int

from .data_source import get_history

__plugin_meta__ = PluginMetadata(
    name="复读历史",
    description="查看历史复读数据",
    usage="""显示2020年1月的数据
/history 2020-1
显示2020年1月1日的数据
/history 2020-1-1""",
    supported_adapters={"~onebot.v11"},
)

history_cmd = repeat.command("history", aliases={"history", "历史", "复读历史"})


@history_cmd.handle()
async def history_handle_first_receive(state: T_State, arg: Message = CommandArg()):
    match = re.match(r"^(\d+)(?:\-(\d+)(?:\-(\d+))?)?$", arg.extract_plain_text())
    if match:
        year = match.group(1)
        month = match.group(2)
        day = match.group(3)
        if year:
            state["year"] = int(year)
        if month:
            state["month"] = int(month)
        if day:
            state["day"] = int(day)


@history_cmd.got(
    "year",
    prompt="你请输入你要查询的年份",
    parameterless=[Depends(parse_int("year"))],
)
@history_cmd.got(
    "month",
    prompt="你请输入你要查询的月份",
    parameterless=[Depends(parse_int("month"))],
)
@history_cmd.got(
    "day",
    prompt="你请输入你要查询的日期（如查询整月排名请输入 0）",
    parameterless=[Depends(parse_int("day"))],
)
async def history_handle_group_message(
    bot: Bot,
    group_info: GroupInfo,
    year: int = Arg(),
    month: int = Arg(),
    day: int = Arg(),
):
    res = await get_history(
        bot,
        year=year,
        month=month,
        day=day,
        group_info=group_info,
    )
    await history_cmd.finish(res)
