"""FFLogs

查询副本输出数据。
"""
from typing import cast

from nonebot.adapters import Event, Message, MessageSegment
from nonebot.adapters.onebot.v11 import Message as OneBotV11Message
from nonebot.adapters.onebot.v12 import Message as OneBotV12Message
from nonebot.params import CommandArg, Depends
from nonebot.plugin import PluginMetadata

from src.utils.helpers import strtobool

from ... import ff14, global_config, plugin_config
from .fflogs_api import fflogs
from .fflogs_data import FFLOGS_DATA

__plugin_meta__ = PluginMetadata(
    name="FFLogs",
    description="副本输出查询",
    usage="""更新副本数据
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
/dps @他人""",
    extra={
        "adapters": ["OneBot V11", "OneBot V12"],
    },
)

fflogs_cmd = ff14.command("dps", aliases={"dps"})


async def get_user(
    args: Message = CommandArg(),
) -> tuple[str, MessageSegment] | None:
    """获取提到的用户信息"""
    if isinstance(args, OneBotV11Message) and (at := args["at"]):
        at = at[0]
        at = cast(MessageSegment, at)
        return at.data["qq"], at
    if isinstance(args, OneBotV12Message) and (mention := args["mention"]):
        mention = mention[0]
        mention = cast(MessageSegment, mention)
        return mention.data["user_id"], mention


@fflogs_cmd.handle()
async def fflogs_handle(
    event: Event,
    args: Message = CommandArg(),
    at_user: tuple[str, MessageSegment] | None = Depends(get_user),
):
    user_id = event.get_user_id()

    argv: list[str | MessageSegment] = list(args.extract_plain_text().split())
    if at_user:
        argv.append(at_user[1])

    if not argv:
        await fflogs_cmd.finish(f"{__plugin_meta__.name}\n\n{__plugin_meta__.usage}")

    # 设置 Token
    if argv[0] == "token" and len(argv) == 2:
        # 检查是否是超级用户
        if user_id not in global_config.superusers:
            await fflogs_cmd.finish("抱歉，你没有权限修改 Token。")

        plugin_config.fflogs_token = str(argv[1])
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
            if strtobool(str(argv[1])):
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
                plugin_config.fflogs_cache_boss.append(str(argv[2]))
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
                "抱歉，你没有绑定最终幻想14的角色。\n请使用\n/dps me 角色名 服务器名\n绑定自己的角色。",
                at_sender=True,
            )
        await fflogs_cmd.finish(
            f"你当前绑定的角色：\n角色：{fflogs.characters[user_id][0]}\n服务器：{fflogs.characters[user_id][1]}",
            at_sender=True,
        )

    if isinstance(argv[0], MessageSegment) and at_user and len(argv) == 1:
        user_id = at_user[0]
        if user_id not in fflogs.characters:
            await fflogs_cmd.finish("抱歉，该用户没有绑定最终幻想14的角色。", at_sender=True)
        await fflogs_cmd.finish(
            at_user[1]
            + f"当前绑定的角色：\n角色：{fflogs.characters[user_id][0]}\n服务器：{fflogs.characters[user_id][1]}"
        )

    if argv[0] == "me" and len(argv) == 3:
        fflogs.set_character(user_id, str(argv[1]), str(argv[2]))
        await fflogs_cmd.finish("角色绑定成功！", at_sender=True)

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
        if (
            not isinstance(argv[0], MessageSegment)
            and isinstance(argv[1], MessageSegment)
            and at_user
        ):
            # @他人的格式
            data = await get_character_dps_by_user_id(argv[0], at_user[0])
        elif (
            not isinstance(argv[0], MessageSegment)
            and isinstance(argv[1], str)
            and argv[1].lower() == "me"
        ):
            data = await get_character_dps_by_user_id(argv[0], user_id)
        else:
            data = await fflogs.dps(*argv)  # type:ignore
        await fflogs_cmd.finish(data)

    if len(argv) == 3:
        # <BOSS名> <职业名> <DPS种类>
        # <BOSS名> <角色名> <服务器名>
        argv[2] = str(argv[2]).lower()
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
