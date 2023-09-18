from nonebot_plugin_datastore import create_session
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .models import Bind, User


async def create_user(pid: str, platform: str, name: str):
    """创建账号"""
    async with create_session() as session:
        user = User(name=name)
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
    """获取账号"""
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
            raise ValueError("找不到用户信息")

        return bind.auser


async def get_user_by_id(uid: int):
    """通过 uid 获取账号"""
    async with create_session() as session:
        user = (await session.scalars(select(User).where(User.id == uid))).one_or_none()

        if not user:
            raise ValueError("找不到用户信息")

        return user


async def set_bind(pid: str, platform: str, aid: int):
    """设置账号绑定"""
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


async def remove_bind(pid: str, platform: str):
    """解除账号绑定"""
    async with create_session() as db_session:
        bind = (
            await db_session.scalars(
                select(Bind).where(Bind.pid == pid).where(Bind.platform == platform)
            )
        ).one()

        if bind.aid == bind.bid:
            return False
        else:
            bind.aid = bind.bid
            await db_session.commit()
            return True


async def get_or_create_user(pid: str, platform: str, name: str):
    """获取一个用户，如果不存在则创建"""
    try:
        user = await get_user(pid, platform)
    except ValueError:
        user = await create_user(pid, platform, name)

    return user
