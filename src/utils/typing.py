from collections.abc import Callable, Sequence
from typing import Annotated, Union

from nonebot.params import Depends
from nonebot_plugin_datastore import get_session
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

Expression_T = Union[str, Sequence[str], Callable[..., str]]
AsyncSession = Annotated[_AsyncSession, Depends(get_session)]
"""可直接注入的 AsyncSession 类型"""
