""" 最终幻想XIV

藏宝选门
FFLogs
"""
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from nonebot import CommandGroup
from nonebot.adapters import Event, Message, MessageSegment
from nonebot.adapters.onebot.v11 import Message as OneBotV11Message
from nonebot.adapters.onebot.v11 import MessageSegment as OneBotV11MessageSegment
from nonebot.adapters.qqguild import Message as QQGuildMessage
from nonebot.adapters.qqguild import MessageSegment as QQGuildMessageSegment
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg, Depends

from src.utils.helpers import strtobool

from .config import DATA, global_config, plugin_config
from .fflogs_api import fflogs
from .fflogs_data import FFLOGS_DATA
from .gate import get_direction
from .nuannuan import get_latest_nuannuan
from .universalis_api import get_item_price

ff14 = CommandGroup("ff14")

# region 藏宝选门
gate_cmd = ff14.command("gate", aliases={"gate"})
gate_cmd.__doc__ = """
最终幻想XIV 藏宝选门

选择门的数量
/gate 2
/gate 3
"""


async def get_door_number(door_number: str = ArgPlainText()) -> int:
    """获取门的数量"""
    if not door_number:
        await gate_cmd.reject("你什么都不输入我怎么知道呢，请告诉我有几个门！")

    if not door_number.isdigit():
        await gate_cmd.reject("门的数量只能是数字！")

    number = int(door_number)
    if number not in [2, 3]:
        await gate_cmd.reject("暂时只支持两个门或者三个门的情况，请重新输入吧。")

    return number


@gate_cmd.handle()
async def gate_handle_first_receive(matcher: Matcher, arg: Message = CommandArg()):
    if arg.extract_plain_text():
        matcher.set_arg("door_number", arg)


@gate_cmd.got("door_number", prompt="总共有多少个门呢？")
async def gate_handle(door_number: Literal[2, 3] = Depends(get_door_number)):
    direction = get_direction(door_number)
    await gate_cmd.finish(direction, at_sender=True)


# endregion
# region FFLogs
fflogs_cmd = ff14.command("dps", aliases={"dps"})
fflogs_cmd.__doc__ = """
最终幻想XIV 输出查询

更新副本数据
/dps update

查询输出排行榜：
/dps 副本名 职业 DPS种类（支持 rdps adps pdps，留空默认为 rdps）
查询指定角色的排名：
/dps 副本名 角色名 服务器名
也可直接查询自己绑定角色的排名：
/dps 副本名 me
或查询他人绑定的角色排名
/dps 副本名 @他人
查询当前QQ号绑定的角色
/dps me
绑定自己的角色
/dps me 角色名 服务器名
查询他人绑定的角色
/dps @他人
"""


@dataclass
class User:
    platform: str
    user_id: str

    def at(self) -> MessageSegment:
        if self.platform == "qq":
            return OneBotV11MessageSegment.at(self.user_id)
        return QQGuildMessageSegment.mention_user(int(self.user_id))


@fflogs_cmd.handle()
async def fflogs_handle(event: Event, args: Message = CommandArg()):
    argv: list[Any] = args.extract_plain_text().split()

    at_message = None
    if isinstance(args, OneBotV11Message):
        at_message = args["at"]
        if at_message:
            argv.append(User("qq", at_message[0].data["qq"]))
    elif isinstance(args, QQGuildMessage):
        at_message = args["mention_user"]
        if at_message:
            argv.append(User("qqguild", at_message[0].data["user_id"]))

    if not argv:
        await fflogs_cmd.finish()

    user_id = event.get_user_id()

    # 设置 Token
    if argv[0] == "token" and len(argv) == 2:
        # 检查是否是超级用户
        if user_id not in global_config.superusers:
            await fflogs_cmd.finish("抱歉，你没有权限修改 Token。")

        plugin_config.fflogs_token = argv[1]
        await fflogs_cmd.finish("Token 设置完成。")

    # 检查 Token 是否设置
    if not plugin_config.fflogs_token:
        await fflogs_cmd.finish(
            "对不起，Token 未设置，无法查询数据。\n请先使用命令\n/dps token <token>\n配置好 Token 后再尝试查询数据。"
        )

    if argv[0] == "token" and len(argv) == 1:
        # 检查是否是超级用户
        if user_id not in global_config.superusers:
            await fflogs_cmd.finish("抱歉，你没有权限查看 Token。")
        await fflogs_cmd.finish(f"当前的 Token 为 {plugin_config.fflogs_token}")

    if argv[0] == "update" and len(argv) == 1:
        await FFLOGS_DATA.update()
        data = await FFLOGS_DATA.data
        await fflogs_cmd.finish(f"副本数据更新成功，当前版本为 {data.version}。")

    # 缓存相关设置
    if argv[0] == "cache":
        if len(argv) == 2:
            if argv[1] == "list":
                if not plugin_config.fflogs_cache_boss:
                    await fflogs_cmd.finish("当前没有缓存副本。")
                await fflogs_cmd.finish(
                    "当前缓存的副本有：\n" + "\n".join(plugin_config.fflogs_cache_boss)
                )
            # 检查是否是超级用户
            if user_id not in global_config.superusers:
                await fflogs_cmd.finish("抱歉，你没有权限设置缓存。")
            if strtobool(argv[1]):
                if not fflogs.is_cache_enabled:
                    fflogs.enable_cache()
                await fflogs_cmd.finish("已开始定时缓存。")
            else:
                if fflogs.is_cache_enabled:
                    fflogs.disable_cache()
                await fflogs_cmd.finish("已停止定时缓存。")
        if len(argv) == 3:
            if argv[1] == "add":
                if not plugin_config.fflogs_cache_boss:
                    plugin_config.fflogs_cache_boss = []
                plugin_config.fflogs_cache_boss.append(argv[2])
                # 触发 validator
                plugin_config.fflogs_cache_boss = plugin_config.fflogs_cache_boss
                await fflogs_cmd.finish(f"已添加副本 {argv[2]}。")
            elif argv[1] == "del":
                if argv[2] in plugin_config.fflogs_cache_boss:
                    plugin_config.fflogs_cache_boss.remove(argv[2])
                    plugin_config.fflogs_cache_boss = plugin_config.fflogs_cache_boss
                    await fflogs_cmd.finish(f"已删除副本 {argv[2]}。")
                else:
                    await fflogs_cmd.finish(f"没有缓存 {argv[2]}，无法删除。")
        else:
            if fflogs.is_cache_enabled:
                await fflogs_cmd.finish("定时缓存开启中")
            else:
                await fflogs_cmd.finish("定时缓存关闭中")

    if argv[0] == "me" and len(argv) == 1:
        if user_id not in fflogs.characters:
            await fflogs_cmd.finish(
                "抱歉，你没有绑定最终幻想14的角色。\n请使用\n/dps me 角色名 服务器名\n绑定自己的角色。"
            )
        await fflogs_cmd.finish(
            f"你当前绑定的角色：\n角色：{fflogs.characters[user_id][0]}\n服务器：{fflogs.characters[user_id][1]}"
        )

    if isinstance(argv[0], User) and len(argv) == 1:
        user_id = argv[0].user_id
        if user_id not in fflogs.characters:
            await fflogs_cmd.finish("抱歉，该用户没有绑定最终幻想14的角色。")
        await fflogs_cmd.finish(
            argv[0].at()
            + f"当前绑定的角色：\n角色：{fflogs.characters[user_id][0]}\n服务器：{fflogs.characters[user_id][1]}"
        )

    if argv[0] == "me" and len(argv) == 3:
        fflogs.set_character(user_id, argv[1], argv[2])
        await fflogs_cmd.finish("角色绑定成功！")

    if argv[0] == "classes" and len(argv) == 1:
        data = await fflogs.classes()
        await fflogs_cmd.finish(str(data.dict()["__root__"]))

    if argv[0] == "zones" and len(argv) == 2:
        data = await fflogs.zones()
        zones = next(filter(lambda x: str(x.id) == argv[1], data))
        await fflogs_cmd.finish(str(zones.dict()))

    # 判断查询排行是指个人还是特定职业
    if len(argv) == 2:
        # <BOSS名> me
        # <BOSS名> <@他人>
        # <BOSS名> <职业名>
        if isinstance(argv[1], User):
            # @他人的格式
            user_id = argv[1].user_id
            data = await get_character_dps_by_user_id(argv[0], user_id)
        elif argv[1].lower() == "me":
            data = await get_character_dps_by_user_id(argv[0], user_id)
        else:
            data = await fflogs.dps(*argv)  # type:ignore
        await fflogs_cmd.finish(data)

    if len(argv) == 3:
        # <BOSS名> <职业名> <DPS种类>
        # <BOSS名> <角色名> <服务器名>
        argv[2] = argv[2].lower()
        if argv[2] in ["adps", "rdps", "pdps"]:
            data = await fflogs.dps(*argv)  # type:ignore
        else:
            data = await fflogs.character_dps(*argv)  # type:ignore
        await fflogs_cmd.finish(data)


async def get_character_dps_by_user_id(boss_nickname: str, user_id: str):
    """通过 BOSS 名称和 QQ 号来获取角色的 DPS 数据"""
    if user_id not in fflogs.characters:
        return "抱歉，你没有绑定最终幻想14的角色。\n请使用\n/dps me <角色名> <服务器名>\n绑定自己的角色。"
    return await fflogs.character_dps(
        boss_nickname,
        *fflogs.characters[user_id],
    )


# endregion
# region 时尚品鉴
nuannuan_cmd = ff14.command("nuannuan", aliases={"时尚品鉴"})
nuannuan_cmd.__doc__ = """
最终幻想XIV 时尚品鉴

获取最新的满分攻略
/时尚品鉴
"""


@nuannuan_cmd.handle()
async def nuannuan_handle():
    """时尚品鉴"""
    latest = await get_latest_nuannuan()
    if latest:
        await nuannuan_cmd.finish(latest)
    else:
        await nuannuan_cmd.finish("抱歉，没有找到最新的满分攻略。")


# endregion
# region 查价
price_cmd = ff14.command("price", aliases={"查价"})
price_cmd.__doc__ = """
最终幻想XIV 价格查询

查询大区中的最低价格
/查价 萨维奈舞裙 猫小胖
查询服务器中的最低价格
/查价 萨维奈舞裙 静语庄园
设置默认查询的区域
/查价 默认值 静语庄园
查询当前设置的默认值
/查价 默认值
"""


@price_cmd.handle()
async def price_handle(event: Event, args: Message = CommandArg()):
    """查价"""
    argv = args.extract_plain_text().split()

    user_id = event.get_user_id()

    if len(argv) == 0:
        await price_cmd.finish()

    if len(argv) == 1 and argv[0] == "默认值":
        world_or_dc = DATA.config.get(f"price-default-{user_id}", "猫小胖")
        await price_cmd.finish(f"当前设置的默认值为：{world_or_dc}")

    if len(argv) == 2 and argv[0] == "默认值":
        DATA.config.set(f"price-default-{user_id}", argv[1])
        await price_cmd.finish("查询区域默认值设置成功！")

    if len(argv) > 0:
        name = argv[0]
        if len(argv) >= 2:
            world_or_dc = argv[1]
        else:
            world_or_dc = DATA.config.get(f"price-default-{user_id}", "猫小胖")

        try:
            reply = await get_item_price(name, world_or_dc)
        except httpx.HTTPError:
            reply = "抱歉，网络出错，请稍后再试。"

        await price_cmd.finish(reply)


# endregion
