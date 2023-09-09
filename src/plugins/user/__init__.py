from nonebot.params import Depends
from nonebot_plugin_alconna import Alconna, Args, on_alconna
from nonebot_plugin_datastore import create_session
from nonebot_plugin_session import Session, extract_session
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.utils.annotated import AsyncSession

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
    assert session.id1 and session.platform

    user = await get_user(session.id1, session.platform)
    if not user:
        user = await create_user(session.id1, session.platform)

    await user_cmd.finish(f"{user.id} {user.name}")


bind_cmd = on_alconna(Alconna("bind", Args["id", int]), use_cmd_start=True)


@bind_cmd.handle()
async def _(
    id: int,
    db: AsyncSession,
    session: Session = Depends(extract_session),
):
    assert session.id1 and session.platform

    auser = (await db.scalars(select(User).where(User.id == id))).one_or_none()
    if not auser:
        await bind_cmd.finish("找不到用户信息")
        return

    await set_user(session.id1, session.platform, auser.id)
