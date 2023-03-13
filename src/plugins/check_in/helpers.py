from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.helpers import GroupOrChannel

from .models import User


async def ensure_user(session: AsyncSession, group_or_channel: GroupOrChannel) -> User:
    """确保用户存在"""
    user = await session.scalar(
        select(User)
        .where(User.user_id == group_or_channel.user_id)
        .where(User.platform == group_or_channel.platform)
    )

    if not user:
        user = User(**group_or_channel.platform_user_id)
        session.add(user)
        await session.commit()

    return user
