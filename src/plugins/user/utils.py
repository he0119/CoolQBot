from nonebot_plugin_datastore import create_session
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .models import Bind, User


async def create_user(pid: str, platform: str, nickname: str):
    async with create_session() as session:
        user = User(name=nickname)
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
