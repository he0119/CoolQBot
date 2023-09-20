from nonebot import require

require("nonebot_plugin_alconna")
require("nonebot_plugin_session")
require("nonebot_plugin_userinfo")
import random
from typing import cast

from expiringdict import ExpiringDict
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaQuery,
    Args,
    Option,
    Query,
    on_alconna,
)
from nonebot_plugin_session import SessionLevel

from .annotated import UserSession as UserSession
from .utils import get_user, remove_bind, set_bind

__plugin_meta__ = PluginMetadata(
    name="用户",
    description="管理和绑定不同平台的用户",
    usage="""查看用户信息
/user
绑定用户
/bind
解除绑定
/bind -r""",
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna", "nonebot_plugin_session", "nonebot_plugin_userinfo"
    ),
)

user_cmd = on_alconna(Alconna("user"), use_cmd_start=True)


@user_cmd.handle()
async def _(session: UserSession):
    await user_cmd.finish(
        "\n".join(
            [
                f"用户 ID：{session.uid}",
                f"用户名：{session.name}",
                f"用户创建日期：{session.created_at}",
                f"用户所在平台 ID：{session.pid}",
                f"用户所在平台：{session.platform}",
            ]
        )
    )


tokens = cast(
    dict[str, tuple[str, str, int, SessionLevel | None]],
    ExpiringDict(max_len=100, max_age_seconds=300),
)


bind_cmd = on_alconna(
    Alconna("bind", Option("-r"), Args["token?", str]), use_cmd_start=True
)


@bind_cmd.handle()
async def _(
    session: UserSession,
    token: str | None = None,
    remove: Query[bool] = AlconnaQuery("r.value", default=False),
):
    if remove.result:
        result = await remove_bind(session.pid, session.platform)
        if result:
            await bind_cmd.finish("解绑成功")
        else:
            await bind_cmd.finish("不能解绑最初绑定的账号")

    # 生成令牌
    if not token:
        token = f"nonebot/{random.randint(100000, 999999)}"
        tokens[token] = (session.pid, session.platform, session.uid, session.level)
        await bind_cmd.finish(
            f"命令 bind 可用于在多个平台间绑定用户数据。绑定过程中，原始平台的用户数据将完全保留，而目标平台的用户数据将被原始平台的数据所覆盖。\n请确认当前平台是你的目标平台，并在 5 分钟内使用你的账号在原始平台内向机器人发送以下文本：\n/bind {token}\n绑定完成后，你可以随时使用「bind -r」来解除绑定状态。"
        )

    # 绑定流程
    if token in tokens:
        # 平台的相关信息
        pid, platform, user_id, level = tokens.pop(token)
        # 群内绑定的第一步，会在原始平台发送令牌
        # 此时 pid 和 platform 为目标平台的信息
        if level == SessionLevel.LEVEL2 or level == SessionLevel.LEVEL3:
            token = f"nonebot/{random.randint(100000, 999999)}"
            tokens[token] = (session.pid, session.platform, user_id, None)
            await bind_cmd.finish(
                f"令牌核验成功！下面将进行第二步操作。\n请在 5 分钟内使用你的账号在目标平台内向机器人发送以下文本：\n/bind {token}\n注意：当前平台是你的原始平台，这里的用户数据将覆盖目标平台的数据。"
            )
        # 群内绑定的第二步，会在目标平台发送令牌
        # 此时 pid 和 platform 为原始平台的信息
        # 需要重新获取其用户信息，然后将目标平台绑定至原始平台
        elif level is None:
            if session.uid != user_id:
                await bind_cmd.finish("请使用最开始要绑定账号进行操作")

            user = await get_user(pid, platform)
            await set_bind(session.pid, session.platform, user.id)
            await bind_cmd.finish("绑定成功")
        # 私聊绑定时，会在原始平台发送令牌
        # 此时 pid 和 platform 为目标平台的信息
        # 直接将目标平台绑定至原始平台
        elif level == SessionLevel.LEVEL1:
            await set_bind(pid, platform, session.uid)
            await bind_cmd.finish("绑定成功")
    else:
        await bind_cmd.finish("令牌不存在或已过期")
