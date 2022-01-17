from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    # FIXME: 如果不添加这句测试时会报错
    # sqlalchemy.exc.InvalidRequestError: Table 'message' is already defined for this MetaData instance.
    # Specify 'extend_existing=True' to redefine options and columns on an existing Table object.
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    time: datetime
    user_id: str
    group_id: str
    message: str
    platform: str
