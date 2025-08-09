"""排行榜"""

import re

from nonebot.adapters.onebot.v11 import Bot as V11Bot
from nonebot.adapters.onebot.v12 import Bot as V12Bot
from nonebot.params import Arg, Depends
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from nonebot_plugin_user import UserSession

from src.utils.helpers import parse_bool, parse_int

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
    supported_adapters={"~onebot.v11", "~onebot.v12"},
)

rank_cmd = on_alconna(
    Alconna(
        "rank",
        Args["arg?#排行榜参数", str],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"复读排行榜"},
    use_cmd_start=True,
    block=True,
)


@rank_cmd.handle()
async def rank_handle_first_receive(state: T_State, arg: Match[str]):
    args = arg.result if arg.available else ""
    match = re.match(r"^(?:(\d+))?(?:n(\d+))?$", args)
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
    user: UserSession,
    display_number: int = Arg(),
    minimal_msg_number: int = Arg(),
    display_total_number: bool = Arg(),
):
    res = await get_rank(
        bot,
        display_number=display_number,
        minimal_msg_number=minimal_msg_number,
        display_total_number=display_total_number,
        session_id=user.session_id,
    )
    await rank_cmd.finish(res)
