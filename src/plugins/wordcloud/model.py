from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    time: Optional[datetime] = Field(default=datetime.now())
    user_id: str
    group_id: str
    message: str
