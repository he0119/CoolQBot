""" 排行榜 """
import re

from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot as V11Bot
from nonebot.adapters.onebot.v12 import Bot as V12Bot
from nonebot.params import Arg, CommandArg, Depends
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from src.utils.helpers import (
    GroupOrChannel,
    get_group_or_channel,
    get_platform,
    parse_bool,
    parse_int,
)

from ... import repeat
from .data_source import get_rank

__plugin_meta__ = PluginMetadata(
    name="复读排行榜",
    description="查看复读排行榜",
    usage="""获取当前的排行榜（默认显示前三名）
/rank
限制进入排行榜所需发送消息的数量
/rank n30
限制显示的人数
/rank 3n30""",
    extra={
        "adapters": ["OneBot V11", "OneBot V12"],
    },
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
    bot: V11Bot | V12Bot,
    display_number: int = Arg(),
    minimal_msg_number: int = Arg(),
    display_total_number: bool = Arg(),
    group_or_channel: GroupOrChannel = Depends(get_group_or_channel),
    platform: str = Depends(get_platform),
):
    res = await get_rank(
        bot,
        display_number=display_number,
        minimal_msg_number=minimal_msg_number,
        display_total_number=display_total_number,
        platform=platform,
        **group_or_channel.group_or_channel_id,
    )
    await rank_cmd.finish(res)
