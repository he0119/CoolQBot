"""群组绑定"""

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_orm")
require("nonebot_plugin_user")
require("nonebot_plugin_alconna")

from nonebot_plugin_alconna import (
    Alconna,
    AlconnaMatcher,
    Args,
    CommandMeta,
    on_alconna,
)
from nonebot_plugin_user import UserSession

from src.utils.permission import SUPERUSER

from .data_source import GroupBindService

__plugin_meta__ = PluginMetadata(
    name="群组绑定",
    description="将多个群组绑定在一起",
    usage="/绑定群组 <目标群组ID>\n/解绑群组\n/查看绑定",
    type="application",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)

# 初始化群组绑定服务
group_bind_service = GroupBindService()

# 绑定群组命令
bind_group_cmd = on_alconna(
    Alconna(
        "绑定群组",
        Args["target_group_id", str],
        meta=CommandMeta(
            description="将当前群组绑定到目标群组",
            usage="绑定群组 <目标群组ID>",
            example="/绑定群组 123456789",
        ),
    ),
    permission=SUPERUSER,
    use_cmd_start=True,
    block=True,
)


@bind_group_cmd.handle()
async def _(matcher: AlconnaMatcher, user: UserSession, target_group_id: str):
    """处理绑定群组命令"""
    current_session_id = user.session_id

    try:
        await group_bind_service.bind_group(current_session_id, target_group_id)
        await matcher.finish(f"✅ 群组绑定成功！当前群组已绑定到群组 {target_group_id}")
    except ValueError as e:
        await matcher.finish(f"❌ 绑定失败：{e!s}")


# 解绑群组命令
unbind_group_cmd = on_alconna(
    Alconna(
        "解绑群组",
        meta=CommandMeta(
            description="将当前群组从绑定中移除",
            usage="解绑群组",
            example="/解绑群组",
        ),
    ),
    permission=SUPERUSER,
    use_cmd_start=True,
    block=True,
)


@unbind_group_cmd.handle()
async def _(matcher: AlconnaMatcher, user: UserSession):
    """处理解绑群组命令"""
    current_session_id = user.session_id

    try:
        await group_bind_service.unbind_group(current_session_id)
        await matcher.finish("✅ 群组解绑成功！当前群组已从绑定中移除")
    except ValueError as e:
        await matcher.finish(f"❌ 解绑失败：{e!s}")


# 查看绑定状态命令
check_bind_cmd = on_alconna(
    Alconna(
        "查看绑定",
        meta=CommandMeta(
            description="查看当前群组的绑定状态",
            usage="查看绑定",
            example="/查看绑定",
        ),
    ),
    permission=SUPERUSER,
    use_cmd_start=True,
    block=True,
)


@check_bind_cmd.handle()
async def _(matcher: AlconnaMatcher, user: UserSession):
    """处理查看绑定状态命令"""
    current_session_id = user.session_id

    # 检查是否已绑定
    is_bound = await group_bind_service.is_group_bound(current_session_id)

    if not is_bound:
        await matcher.finish("📝 当前群组未绑定到任何群组")

    # 获取绑定的目标群组ID
    bind_id = await group_bind_service.get_bind_id(current_session_id)

    # 获取所有绑定到同一目标的群组
    bound_session_ids = await group_bind_service.get_bound_session_ids(current_session_id)

    if bind_id == current_session_id:
        # 当前群组是目标群组
        other_groups = [sid for sid in bound_session_ids if sid != current_session_id]
        if other_groups:
            groups_text = "\n".join(f"  - {group_id}" for group_id in other_groups)
            await matcher.finish(f"📝 当前群组是绑定目标群组\n\n以下群组绑定到此群组：\n{groups_text}")
        else:
            await matcher.finish("📝 当前群组是绑定目标群组，但没有其他群组绑定到此群组")
    else:
        # 当前群组绑定到其他群组
        await matcher.finish(f"📝 当前群组已绑定到群组: {bind_id}")
