from typing import Annotated

from nonebot.params import Depends

from .params import get_session_id

SessionId = Annotated[str, Depends(get_session_id)]
"""合并后的会话 ID"""
