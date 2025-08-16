from typing import Annotated

from nonebot import require

require("nonebot_plugin_user")
require("src.utils.group_bind")
from nonebot.params import Depends
from nonebot_plugin_uninfo import Session, get_session
from nonebot_plugin_user import User
from nonebot_plugin_user.models import UserSession as _UserSession

from src.utils.group_bind import group_bind_service


async def get_user_session(user: User, session: Session | None = Depends(get_session)):
    """获取用户会话"""
    if session is None:
        return None

    session_id = f"{session.scope}_{session.scene_path}"
    session_id = await group_bind_service.get_bind_id(session_id)

    if user:

        class NewUserSession(_UserSession):
            @property
            def session_id(self):
                return session_id

        user_session = NewUserSession(session=session, user=user)
        return user_session


UserSession = Annotated[_UserSession, Depends(get_user_session)]


def patch_user():
    import nonebot_plugin_user

    nonebot_plugin_user.UserSession = UserSession
    nonebot_plugin_user.annotated.UserSession = UserSession
