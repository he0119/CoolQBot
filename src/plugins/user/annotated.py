from typing import Annotated

from nonebot.params import Depends

from .depends import UserSession as _UserSession
from .depends import get_or_create_user, get_user_session
from .models import User as _User

User = Annotated[_User, Depends(get_or_create_user)]
UserSession = Annotated[_UserSession, Depends(get_user_session)]
