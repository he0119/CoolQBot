""" nonebot-bison

修改自 https://github.com/felinae98/nonebot-bison
基于 0.4.0 版本
"""
import re

import httpx
from nonebot import CommandGroup
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgStr, Depends, State
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

from .config import Config
from .platform import check_sub_target, platform_manager
from .scheduler import *
from .types import Target
from .utils import parse_text

common_platform = [
    p.platform_name
    for p in filter(
        lambda platform: platform.enabled and platform.is_common,
        platform_manager.values(),
    )
]

sub = CommandGroup("sub")

# region 添加订阅
add_sub_cmd = sub.command(
    "add", aliases={"添加订阅"}, permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER
)
add_sub_cmd.__doc__ = """
订阅

仅允许群主与管理员操作
/添加订阅
"""


@add_sub_cmd.handle()
async def init_promote(event: GroupMessageEvent, state: T_State = State()):
    state["_prompt"] = (
        "请输入想要订阅的平台，目前支持：\n"
        + "".join(
            [
                "{}：{}\n".format(platform_name, platform_manager[platform_name].name)
                for platform_name in common_platform
            ]
        )
        + '要查看全部平台请输入："全部"'
    )


async def parse_platform(event: GroupMessageEvent, state: T_State = State()) -> None:
    platform = event.get_plaintext().strip()
    if platform == "全部":
        message = "全部平台\n" + "\n".join(
            [
                "{}：{}".format(platform_name, platform.name)
                for platform_name, platform in platform_manager.items()
            ]
        )
        await add_sub_cmd.reject(message)
    elif platform in platform_manager:
        state["platform"] = platform
    else:
        await add_sub_cmd.reject("平台输入错误")


@add_sub_cmd.got("platform", Message.template("{_prompt}"), [Depends(parse_platform)])
async def init_id(platform: str = Arg(), state: T_State = State()):
    if platform_manager[platform].has_target:  # type: ignore
        state["_prompt"] = "请输入订阅用户的 ID"
    else:
        state["id"] = "default"
        state["name"] = await platform_manager[platform].get_target_name(Target(""))


async def parse_id(event: GroupMessageEvent, state: T_State = State()):
    target = str(event.get_message()).strip()
    try:
        name = await check_sub_target(state["platform"], target)
        if not name:
            await add_sub_cmd.reject("ID 输入错误")
        state["id"] = target
        state["name"] = name
    except httpx.ConnectTimeout:
        await add_sub_cmd.finish(f"验证 ID 失败，网络连接超时，请稍后再试")
    except httpx.ConnectError:
        await add_sub_cmd.finish(f"验证 ID 失败，网络连接错误，请稍后再试")


@add_sub_cmd.got("id", Message.template("{_prompt}"), [Depends(parse_id)])
async def init_cat(event: GroupMessageEvent, state: T_State = State()):
    if not platform_manager[state["platform"]].categories:
        state["cats"] = []
        return
    state["_prompt"] = "请输入要订阅的类别，以逗号分隔，支持的类别有：{}".format(
        "，".join(list(platform_manager[state["platform"]].categories.values()))
    )


async def parser_cats(event: GroupMessageEvent, state: T_State = State()):
    if not isinstance(state["cats"], Message):
        return
    res = []
    for cat in filter(None, re.split(r",|，", str(event.get_message()).strip())):
        if cat not in platform_manager[state["platform"]].reverse_category:
            await add_sub_cmd.reject("不支持 {}".format(cat))
        res.append(platform_manager[state["platform"]].reverse_category[cat])
    state["cats"] = res


@add_sub_cmd.got("cats", Message.template("{_prompt}"), [Depends(parser_cats)])
async def init_tag(event: GroupMessageEvent, state: T_State = State()):
    if not platform_manager[state["platform"]].enable_tag:
        state["tags"] = []
        return
    state["_prompt"] = '请输入要订阅的标签，以逗号分隔，订阅所有标签输入"全部标签"'


async def parser_tags(event: GroupMessageEvent, state: T_State = State()):
    if not isinstance(state["tags"], Message):
        return
    if str(event.get_message()).strip() == "全部标签":
        state["tags"] = []
    else:
        state["tags"] = list(
            filter(None, re.split(r",|，", str(event.get_message()).strip()))
        )


@add_sub_cmd.got("tags", Message.template("{_prompt}"), [Depends(parser_tags)])
async def add_sub_process(event: GroupMessageEvent, state: T_State = State()):
    config = Config()
    config.add_subscribe(
        state.get("_user_id") or event.group_id,
        user_type="group",
        target=state["id"],
        target_name=state["name"],
        target_type=state["platform"],
        cats=state.get("cats", []),
        tags=state.get("tags", []),
    )

    await add_sub_cmd.finish("添加 {} 成功".format(state["name"]))


# endregion
# region 查询订阅
query_sub_cmd = sub.command("query", aliases={"查询订阅"})
query_sub_cmd.__doc__ = """
订阅

/查询订阅
"""


@query_sub_cmd.handle()
async def _(event: GroupMessageEvent, state: T_State = State()):
    config: Config = Config()
    sub_list = config.list_subscribe(state.get("_user_id") or event.group_id, "group")
    res = ["订阅的帐号为："]
    for sub in sub_list:
        temp = "{} {} {}".format(sub["target_type"], sub["target_name"], sub["target"])
        platform = platform_manager[sub["target_type"]]
        if platform.categories:
            temp += " [{}]".format(
                ", ".join(map(lambda x: platform.categories[x], sub["cats"]))
            )
        if platform.enable_tag:
            temp += " {}".format(", ".join(sub["tags"]))
        res.append(temp)
    if len(res) == 1:
        res = "当前无订阅"
    else:
        res = "\n".join(res)
    await query_sub_cmd.finish(Message(await parse_text(res)))


# endregion
# region 删除订阅
del_sub_cmd = sub.command(
    "del", aliases={"删除订阅"}, permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER
)
del_sub_cmd.__doc__ = """
订阅

仅允许群主与管理员操作
/删除订阅
"""


@del_sub_cmd.handle()
async def send_list(bot: Bot, event: GroupMessageEvent, state: T_State = State()):
    config: Config = Config()
    sub_list = config.list_subscribe(event.group_id, "group")
    res = "订阅的帐号为：\n"
    state["sub_table"] = {}
    if not sub_list:
        await del_sub_cmd.finish("当前无订阅")
    for index, sub in enumerate(sub_list, 1):
        state["sub_table"][index] = {
            "target_type": sub["target_type"],
            "target": sub["target"],
        }
        res += "{} {} {} {}".format(
            index, sub["target_type"], sub["target_name"], sub["target"]
        )
        platform = platform_manager[sub["target_type"]]
        if platform.categories:
            res += " [{}]".format(
                ", ".join(map(lambda x: platform.categories[x], sub["cats"]))
            )
        if platform.enable_tag:
            res += " {}".format(", ".join(sub["tags"]))
        res += "\n"
    res += "请输入要删除的订阅的序号"
    await bot.send(event=event, message=Message(await parse_text(res)))


@del_sub_cmd.receive()
async def do_del(event: GroupMessageEvent, state: T_State = State()):
    try:
        index = int(str(event.get_message()).strip())
        config = Config()
        config.del_subscribe(event.group_id, "group", **state["sub_table"][index])
    except Exception as e:
        logger.warning(e)
        await del_sub_cmd.reject("删除错误")
    else:
        await del_sub_cmd.finish("删除成功")


# endregion
