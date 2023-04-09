from sqlalchemy import select

from src.utils.helpers import UserInfo
from src.utils.typing import AsyncSession

from .models import User


async def ensure_user(session: AsyncSession, user_info: UserInfo) -> User:
    """确保用户存在"""
    user = await session.scalar(
        select(User)
        .where(User.user_id == user_info.user_id)
        .where(User.platform == user_info.platform)
    )

    if not user:
        user = User(**user_info.dict())
        session.add(user)
        await session.commit()

    return user
