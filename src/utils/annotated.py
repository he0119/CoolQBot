from typing import Annotated

from nonebot.params import Depends
from nonebot_plugin_datastore import get_session
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

from .depends import (
    get_group_info,
    get_mentioned_user,
    get_plaintext_args,
    get_platform,
    get_user_info,
)
from .models import GroupInfo as _GroupInfo
from .models import MentionedUser as _MentionedUser
from .models import UserInfo as _UserInfo

AsyncSession = Annotated[_AsyncSession, Depends(get_session)]
UserInfo = Annotated[_UserInfo, Depends(get_user_info)]
GroupInfo = Annotated[_GroupInfo, Depends(get_group_info)]
MentionedUser = Annotated[_MentionedUser, Depends(get_mentioned_user)]
OptionalMentionedUser = Annotated[_MentionedUser | None, Depends(get_mentioned_user)]
PlainTextArgs = Annotated[str, Depends(get_plaintext_args)]
OptionalPlainTextArgs = Annotated[str | None, Depends(get_plaintext_args)]
Platform = Annotated[str, Depends(get_platform)]
OptionalPlatform = Annotated[str | None, Depends(get_platform)]
