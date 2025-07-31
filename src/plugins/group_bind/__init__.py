"""群组绑定"""

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.rule import Rule

require("nonebot_plugin_orm")
require("nonebot_plugin_user")
require("nonebot_plugin_alconna")
require("nonebot_plugin_uninfo")

from nonebot_plugin_alconna import (
    Alconna,
    AlconnaMatcher,
    Args,
    CommandMeta,
    on_alconna,
)
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_uninfo import SceneType, Session, UniSession
from nonebot_plugin_user import UserSession

from src.utils.permission import SUPERUSER

from .annotated import SessionId as SessionId
from .data_source import group_bind_service

__plugin_meta__ = PluginMetadata(
    name="群组绑定",
    description="将多个群组绑定在一起",
    usage="/绑定群组 <目标群组ID>\n/解绑群组\n/查看绑定",
    type="application",
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna",
        "nonebot_plugin_user",
        "nonebot_plugin_uninfo",
    ),
)


async def is_group(session: Session = UniSession()) -> bool:
    """确保在群组中使用"""
    return session.scene.type in [
        SceneType.GROUP,
        SceneType.GUILD,
        SceneType.CHANNEL_TEXT,
    ]


# 绑定群组命令
bind_group_cmd = on_alconna(
    Alconna(
        "bind_group",
        Args["target_group_id", str],
        meta=CommandMeta(
            description="将当前群组绑定到目标群组",
            usage="绑定群组 <目标群组ID>",
            example="/绑定群组 123456789",
        ),
    ),
    aliases={"绑定群组"},
    permission=SUPERUSER,
    use_cmd_start=True,
    block=True,
    rule=Rule(is_group),
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh_CN": "绑定群组"}),
    ],
)


@bind_group_cmd.handle()
async def _(matcher: AlconnaMatcher, user: UserSession, target_group_id: str):
    """处理绑定群组命令"""
    current_session_id = user.session_id

    if current_session_id == target_group_id:
        await matcher.finish("不能将当前群组绑定到自己！")

    # 检查是否已经绑定
    is_bound = await group_bind_service.is_group_bound(current_session_id)

    if is_bound:
        old_bind_id = await group_bind_service.get_bind_id(current_session_id)
        await group_bind_service.bind_group(current_session_id, target_group_id)
        await matcher.finish(f"群组绑定已更新！原绑定群组 {old_bind_id} → 新绑定群组 {target_group_id}")
    else:
        await group_bind_service.bind_group(current_session_id, target_group_id)
        await matcher.finish(f"群组绑定成功！当前群组已绑定到群组 {target_group_id}")


# 解绑群组命令
unbind_group_cmd = on_alconna(
    Alconna(
        "unbind-group",
        meta=CommandMeta(
            description="将当前群组从绑定中移除",
            usage="解绑群组",
            example="/解绑群组",
        ),
    ),
    aliases={"解绑群组"},
    permission=SUPERUSER,
    use_cmd_start=True,
    block=True,
    rule=Rule(is_group),
    extensions=[TelegramSlashExtension(), DiscordSlashExtension(name_localizations={"zh_CN": "解绑群组"})],
)


@unbind_group_cmd.handle()
async def _(matcher: AlconnaMatcher, user: UserSession):
    """处理解绑群组命令"""
    current_session_id = user.session_id

    try:
        await group_bind_service.unbind_group(current_session_id)
        await matcher.finish("群组解绑成功！当前群组已从绑定中移除")
    except ValueError as e:
        await matcher.finish(f"解绑失败：{e!s}")


# 查看绑定状态命令
check_bind_cmd = on_alconna(
    Alconna(
        "check-bind",
        meta=CommandMeta(
            description="查看当前群组的绑定状态",
            usage="查看绑定",
            example="/查看绑定",
        ),
    ),
    aliases={"查看绑定"},
    permission=SUPERUSER,
    use_cmd_start=True,
    block=True,
    rule=Rule(is_group),
    extensions=[TelegramSlashExtension(), DiscordSlashExtension(name_localizations={"zh_CN": "查看绑定"})],
)


@check_bind_cmd.handle()
async def _(matcher: AlconnaMatcher, user: UserSession):
    """处理查看绑定状态命令"""
    current_session_id = user.session_id

    # 检查是否已绑定
    is_bound = await group_bind_service.is_group_bound(current_session_id)

    if not is_bound:
        await matcher.finish("当前群组未绑定到任何群组")

    # 获取绑定的目标群组ID
    bind_id = await group_bind_service.get_bind_id(current_session_id)

    await matcher.finish(f"当前群组已绑定到群组: {bind_id}")
