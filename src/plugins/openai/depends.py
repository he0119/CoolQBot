from nonebot_plugin_user import UserSession

from .data_source import Assistant


async def get_assistant(user: UserSession) -> Assistant:
    assistant = Assistant(user.group_session_id)
    await assistant.init()
    return assistant
