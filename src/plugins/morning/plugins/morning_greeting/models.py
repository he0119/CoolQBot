from nonebot_plugin_datastore import get_plugin_data
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

Model = get_plugin_data().Model


class MorningGreeting(MappedAsDataclass, Model):
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "bot_id",
            "group_id",
            "guild_id",
            "channel_id",
            name="unique_morning_greeting",
        ),
    )

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    platform: Mapped[str]
    bot_id: Mapped[str]
    group_id: Mapped[str] = mapped_column(default="")
    guild_id: Mapped[str] = mapped_column(default="")
    channel_id: Mapped[str] = mapped_column(default="")
