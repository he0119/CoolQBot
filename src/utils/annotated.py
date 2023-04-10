from typing import Annotated

from nonebot.params import Depends
from nonebot_plugin_datastore import get_session
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

from .helpers import GroupInfo as _GroupInfo
from .helpers import MentionedUser as _MentionedUser
from .helpers import UserInfo as _UserInfo
from .helpers import get_group_info, get_mentioned_user, get_user_info

AsyncSession = Annotated[_AsyncSession, Depends(get_session)]
UserInfo = Annotated[_UserInfo, Depends(get_user_info)]
GroupInfo = Annotated[_GroupInfo, Depends(get_group_info)]
MentionedUser = Annotated[_MentionedUser | None, Depends(get_mentioned_user)]
