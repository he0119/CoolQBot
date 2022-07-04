"""FFLogs

查询副本输出数据。
"""
from dataclasses import dataclass
from typing import Any

from nonebot.adapters import Event, Message, MessageSegment
from nonebot.adapters.onebot.v11 import Message as OneBotV11Message
from nonebot.adapters.onebot.v11 import MessageSegment as OneBotV11MessageSegment
from nonebot.adapters.qqguild import Message as QQGuildMessage
from nonebot.adapters.qqguild import MessageSegment as QQGuildMessageSegment
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

from src.utils.helpers import strtobool

from ... import ff14, global_config, plugin_config
from .fflogs_api import fflogs
from .fflogs_data import FFLOGS_DATA

__plugin_meta__ = PluginMetadata(
    name="FFLogs",
    description="副本输出查询",
    usage="更新副本数据\n/dps update\n\n查询输出排行榜：\n/dps 副本名 职业 DPS种类（支持 rdps adps pdps，留空默认为 rdps）\n查询指定角色的排名：\n/dps 副本名 角色名 服务器名\n也可直接查询自己绑定角色的排名：\n/dps 副本名 me\n或查询他人绑定的角色排名\n/dps 副本名 @他人\n查询当前QQ号绑定的角色\n/dps me\n绑定自己的角色\n/dps me 角色名 服务器名\n查询他人绑定的角色\n/dps @他人",
)

fflogs_cmd = ff14.command("dps", aliases={"dps"})


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
        await fflogs_cmd.finish(f"{__plugin_meta__.name}\n\n{__plugin_meta__.usage}")

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
        if not isinstance(argv[0], User) and isinstance(argv[1], User):
            # @他人的格式
            user_id = argv[1].user_id
            data = await get_character_dps_by_user_id(argv[0], user_id)
        elif not isinstance(argv[0], User) and argv[1].lower() == "me":
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

    await fflogs_cmd.finish(f"{__plugin_meta__.name}\n\n{__plugin_meta__.usage}")


async def get_character_dps_by_user_id(boss_nickname: str, user_id: str):
    """通过 BOSS 名称和 QQ 号来获取角色的 DPS 数据"""
    if user_id not in fflogs.characters:
        return "抱歉，你没有绑定最终幻想14的角色。\n请使用\n/dps me <角色名> <服务器名>\n绑定自己的角色。"
    return await fflogs.character_dps(
        boss_nickname,
        *fflogs.characters[user_id],
    )


# endregion
