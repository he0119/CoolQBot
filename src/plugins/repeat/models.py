from datetime import date

from nonebot_plugin_datastore import get_plugin_data
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

Model = get_plugin_data().Model


class Record(Model):
    __table_args__ = (
        UniqueConstraint(
            "date",
            "platform",
            "group_id",
            "guild_id",
            "channel_id",
            "user_id",
            name="unique_record",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date]
    platform: Mapped[str]
    group_id: Mapped[str] = mapped_column(default="")
    guild_id: Mapped[str] = mapped_column(default="")
    channel_id: Mapped[str] = mapped_column(default="")

    user_id: Mapped[str]
    repeat_time: Mapped[int] = mapped_column(default=0)
    msg_number: Mapped[int] = mapped_column(default=0)


class Enabled(Model):
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "group_id",
            "guild_id",
            "channel_id",
            name="unique_enabled",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str]
    group_id: Mapped[str] = mapped_column(default="")
    guild_id: Mapped[str] = mapped_column(default="")
    channel_id: Mapped[str] = mapped_column(default="")
