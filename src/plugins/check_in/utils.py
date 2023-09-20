from sqlalchemy import select

from src.user import UserSession
from src.utils.annotated import AsyncSession

from .models import UserInfo


async def get_or_create_user_info(
    user: UserSession, session: AsyncSession, commit: bool = False
):
    """获取用户信息，如果不存在则创建"""

    user_info = (
        await session.scalars(select(UserInfo).where(UserInfo.user_id == user.uid))
    ).one_or_none()

    if not user_info:
        user_info = UserInfo(user_id=user.uid)
        session.add(user_info)

    if commit:
        await session.commit()

    return user_info
