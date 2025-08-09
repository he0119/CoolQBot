from datetime import date

from nonebot_plugin_orm import Model
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class MessageRecord(Model):
    __table_args__ = (UniqueConstraint("date", "session_id", "user_id", name="unique_record"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date]
    session_id: Mapped[str]

    user_id: Mapped[str]
    repeat_time: Mapped[int] = mapped_column(default=0)
    msg_number: Mapped[int] = mapped_column(default=0)


class Enabled(Model):
    __table_args__ = (UniqueConstraint("session_id", name="unique_enabled"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str]
