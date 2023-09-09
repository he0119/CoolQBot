import random
from typing import cast

from expiringdict import ExpiringDict
from nonebot.params import Depends
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaQuery,
    Args,
    Option,
    Query,
    on_alconna,
)
from nonebot_plugin_datastore import create_session
from nonebot_plugin_session import Session, SessionLevel, extract_session
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .models import Bind, User


async def create_user(pid: str, platform: str):
    async with create_session() as session:
        user = User(name=pid)
        session.add(user)
        bind = Bind(
            pid=pid,
            platform=platform,
            auser=user,
            buser=user,
        )
        session.add(bind)
        await session.commit()
        await session.refresh(user)
        return user


async def get_user(pid: str, platform: str):
    async with create_session() as session:
        bind = (
            await session.scalars(
                select(Bind)
                .where(Bind.pid == pid)
                .where(Bind.platform == platform)
                .options(selectinload(Bind.auser))
            )
        ).one_or_none()

        if not bind:
            return

        return bind.auser


async def set_user(pid: str, platform: str, aid: int):
    async with create_session() as session:
        bind = (
            await session.scalars(
                select(Bind).where(Bind.pid == pid).where(Bind.platform == platform)
            )
        ).one_or_none()

        if not bind:
            raise ValueError("找不到用户信息")

        bind.aid = aid
        await session.commit()


user_cmd = on_alconna(Alconna("user"), use_cmd_start=True)


@user_cmd.handle()
async def _(session: Session = Depends(extract_session)):
    if session.platform == "unknown":
        await bind_cmd.finish("不支持的平台")

    assert session.id1 and session.platform

    user = await get_user(session.id1, session.platform)
    if not user:
        user = await create_user(session.id1, session.platform)

    await user_cmd.finish(f"{user.id} {user.name}")


tokens = cast(
    dict[str, tuple[str, str, int, SessionLevel | None]],
    ExpiringDict(max_len=100, max_age_seconds=300),
)


bind_cmd = on_alconna(
    Alconna("bind", Option("-r"), Args["token?", str]), use_cmd_start=True
)


@bind_cmd.handle()
async def _(
    token: str | None = None,
    remove: Query[bool] = AlconnaQuery("r.value", default=False),
    session: Session = Depends(extract_session),
):
    if (
        session.platform == "unknown"
        or session.level == SessionLevel.LEVEL0
        or not session.id1
    ):
        await bind_cmd.finish("不支持的平台")
        return

    user = await get_user(session.id1, session.platform)
    if not user:
        user = await create_user(session.id1, session.platform)

    if remove.result:
        async with create_session() as db_session:
            bind = (
                await db_session.scalars(
                    select(Bind)
                    .where(Bind.pid == session.id1)
                    .where(Bind.platform == session.platform)
                )
            ).one()

            if bind.aid == bind.bid:
                await bind_cmd.finish("不能解绑最初绑定的账号")
            else:
                bind.aid = bind.bid
                await db_session.commit()
                await bind_cmd.finish("解绑成功")

    # 生成令牌
    if not token:
        token = f"nonebot/{random.randint(100000, 999999)}"
        tokens[token] = (session.id1, session.platform, user.id, session.level)
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
            tokens[token] = (session.id1, session.platform, user_id, None)
            await bind_cmd.finish(
                f"令牌核验成功！下面将进行第二步操作。\n请在 5 分钟内使用你的账号在目标平台内向机器人发送以下文本：\n/bind {token}\n注意：当前平台是你的原始平台，这里的用户数据将覆盖目标平台的数据。"
            )
        # 群内绑定的第二步，会在目标平台发送令牌
        # 此时 pid 和 platform 为原始平台的信息
        # 需要重新获取其用户信息，然后将目标平台绑定至原始平台
        elif level is None:
            if user.id != user_id:
                await bind_cmd.finish("请使用最开始要绑定账号进行操作")

            user = await get_user(pid, platform)
            assert user
            await set_user(session.id1, session.platform, user.id)
            await bind_cmd.finish("绑定成功")
        # 私聊绑定时，会在原始平台发送令牌
        # 此时 pid 和 platform 为目标平台的信息
        # 直接将目标平台绑定至原始平台
        elif level == SessionLevel.LEVEL1:
            await set_user(pid, platform, user.id)
            await bind_cmd.finish("绑定成功")
    else:
        await bind_cmd.finish("令牌无效/已过期")
