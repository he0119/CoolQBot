from nonebot_plugin_orm import Model
from nonebot_plugin_saa import PlatformTarget
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class Hello(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    target: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    bot_id: Mapped[str]

    @property
    def saa_target(self) -> PlatformTarget:
        return PlatformTarget.deserialize(self.target)
