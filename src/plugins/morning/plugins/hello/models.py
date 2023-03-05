from nonebot_plugin_datastore import get_plugin_data
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

Model = get_plugin_data().Model


class Hello(Model):
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "group_id",
            "guild_id",
            "channel_id",
            name="unique_hello",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str]
    group_id: Mapped[str] = mapped_column(default="")
    guild_id: Mapped[str] = mapped_column(default="")
    channel_id: Mapped[str] = mapped_column(default="")
