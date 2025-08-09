from typing import Annotated

from nonebot.params import Depends
from nonebot_plugin_orm import get_scoped_session
from sqlalchemy.ext.asyncio import async_scoped_session

from .depends import get_plaintext_args

AsyncSession = Annotated[async_scoped_session, Depends(get_scoped_session)]
PlainTextArgs = Annotated[str, Depends(get_plaintext_args)]
OptionalPlainTextArgs = Annotated[str | None, Depends(get_plaintext_args)]
