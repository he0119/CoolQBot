from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    """消息记录"""

    id: Optional[int] = Field(default=None, primary_key=True)
    time: datetime
    """ 消息时间

    存放 UTC 时间
    """
    user_id: str
    group_id: str
    message: str
    platform: str
