from dataclasses import dataclass
from datetime import datetime

from nonebot.matcher import Matcher
from nonebot.params import Depends
from nonebot_plugin_session import SessionLevel
from nonebot_plugin_userinfo import EventUserInfo, UserInfo

from src.utils.annotated import MyUserInfo, Session

from . import utils
from .models import User


async def get_or_create_user(
    matcher: Matcher,
    session: Session,
    user_info: UserInfo | None = EventUserInfo(),
):
    """获取一个用户，如果不存在则创建"""
    if (
        session.platform == "unknown"
        or user_info is None
        or session.level == SessionLevel.LEVEL0
        or not session.id1
    ):
        await matcher.finish("用户相关功能暂不支持当前平台")
        return

    try:
        user = await utils.get_user(session.id1, session.platform)
    except ValueError:
        user = await utils.create_user(
            session.id1, session.platform, user_info.user_name
        )

    return user


@dataclass
class UserSession:
    session: Session
    info: MyUserInfo
    user: User = Depends(get_or_create_user)

    @property
    def uid(self) -> int:
        """用户 ID"""
        return self.user.id

    @property
    def name(self) -> str:
        """用户名"""
        return self.user.name

    @property
    def created_at(self) -> datetime:
        """用户创建日期"""
        return self.user.created_at

    @property
    def pid(self) -> str:
        """用户所在平台 ID"""
        assert self.session.id1
        return self.session.id1

    @property
    def platform(self) -> str:
        """用户所在平台"""
        return self.session.platform

    @property
    def level(self) -> SessionLevel:
        """用户会话级别"""
        return self.session.level
