"""大模型入口的共用匹配规则。"""

from nonebot_plugin_user import UserSession


async def is_non_private(user: UserSession) -> bool:
    """拒绝私聊，允许群聊、频道和子频道事件。"""
    return not user.session.scene.is_private
