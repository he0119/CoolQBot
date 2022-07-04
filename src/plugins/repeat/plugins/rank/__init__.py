""" 排行榜 """
import re

from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    PrivateMessageEvent,
)
from nonebot.params import Arg, CommandArg, Depends
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from src.utils.helpers import parse_bool, parse_int

from ... import repeat
from .data_source import get_rank

__plugin_meta__ = PluginMetadata(
    name="复读排行榜",
    description="查看复读排行榜",
    usage="获取当前的排行榜（默认显示前三名）\n/rank\n限制进入排行榜所需发送消息的数量\n/rank n30\n限制显示的人数\n/rank 3n30",
)

rank_cmd = repeat.command("rank", aliases={"rank", "排行榜"})


@rank_cmd.handle()
async def rank_handle_first_receive(state: T_State, arg: Message = CommandArg()):
    match = re.match(r"^(?:(\d+))?(?:n(\d+))?$", arg.extract_plain_text())
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

        state["display_number"] = display_number
        state["minimal_msg_number"] = minimal_msg_number
        state["display_total_number"] = display_total_number


@rank_cmd.got(
    "display_number",
    prompt="请输入想显示的排行条数",
    parameterless=[Depends(parse_int("display_number"))],
)
@rank_cmd.got(
    "minimal_msg_number",
    prompt="请输入进入排行，最少需要发送多少消息",
    parameterless=[Depends(parse_int("minimal_msg_number"))],
)
@rank_cmd.got(
    "display_total_number",
    prompt="是否显示每个人发送的消息总数",
    parameterless=[Depends(parse_bool("display_total_number"))],
)
async def rank_handle_group_message(
    bot: Bot,
    event: GroupMessageEvent,
    display_number: int = Arg(),
    minimal_msg_number: int = Arg(),
    display_total_number: bool = Arg(),
):
    res = await get_rank(
        bot,
        display_number=display_number,
        minimal_msg_number=minimal_msg_number,
        display_total_number=display_total_number,
        group_id=event.group_id,
    )
    await rank_cmd.finish(res)


@rank_cmd.got(
    "display_number",
    prompt="请输入想显示的排行条数",
    parameterless=[Depends(parse_int("display_number"))],
)
@rank_cmd.got(
    "minimal_msg_number",
    prompt="请输入进入排行，最少需要发送多少消息",
    parameterless=[Depends(parse_int("minimal_msg_number"))],
)
@rank_cmd.got(
    "display_total_number",
    prompt="是否显示每个人发送的消息总数",
    parameterless=[Depends(parse_bool("display_total_number"))],
)
@rank_cmd.got(
    "group_id",
    prompt="请问你想查询哪个群？",
    parameterless=[Depends(parse_int("group_id"))],
)
async def rank_handle_private_message(
    bot: Bot,
    event: PrivateMessageEvent,
    display_number: int = Arg(),
    minimal_msg_number: int = Arg(),
    display_total_number: bool = Arg(),
    group_id: int = Arg(),
):
    res = await get_rank(
        bot,
        display_number=int(display_number),
        minimal_msg_number=int(minimal_msg_number),
        display_total_number=display_total_number,
        group_id=int(group_id),
    )
    await rank_cmd.finish(res)


# endregion
