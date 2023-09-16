from nonebot.matcher import Matcher
from nonebot.params import Depends
from nonebot_plugin_session import Session, SessionLevel, extract_session
from nonebot_plugin_userinfo import EventUserInfo, UserInfo

from . import utils
from .models import UserSession


async def get_or_create_user(
    matcher: Matcher,
    session: Session = Depends(extract_session),
    user_info: UserInfo | None = EventUserInfo(),
):
    """获取一个用户，如果不存在则创建"""
    if (
        session.platform == "unknown"
        or session.level == SessionLevel.LEVEL0
        or not session.id1
    ):
        await matcher.finish("用户相关功能暂不支持当前平台")
        raise ValueError("用户相关功能暂不支持当前平台")

    user = await utils.get_or_create_user(
        session.id1,
        session.platform,
        user_info and user_info.user_name or session.id1,
    )

    return user


async def get_user_session(
    matcher: Matcher,
    session: Session = Depends(extract_session),
    user_info: UserInfo | None = EventUserInfo(),
):
    """获取用户会话"""
    user = await get_or_create_user(matcher, session, user_info)
    return UserSession(session, user_info, user)
