from nonebot_plugin_user import UserSession
from sqlalchemy import select

from src.utils.annotated import AsyncSession

from .models import UserInfo


async def get_or_create_user_info(
    user: UserSession, session: AsyncSession, commit: bool = False
):
    """获取用户信息，如果不存在则创建"""

    user_info = (
        await session.scalars(select(UserInfo).where(UserInfo.user_id == user.user_id))
    ).one_or_none()

    if not user_info:
        user_info = UserInfo(user_id=user.user_id)
        session.add(user_info)

    if commit:
        await session.commit()

    return user_info
