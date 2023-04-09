from typing import Annotated

from nonebot.params import Depends
from nonebot_plugin_datastore import get_session
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

AsyncSession = Annotated[_AsyncSession, Depends(get_session)]
"""可直接注入的 AsyncSession 类型"""
