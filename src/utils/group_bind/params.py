from nonebot_plugin_user import UserSession

from .data_source import group_bind_service


async def get_session_id(user: UserSession) -> str:
    """获取用户会话的 session_id"""
    return await group_bind_service.get_bind_id(user.session_id)
