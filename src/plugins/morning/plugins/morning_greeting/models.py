from nonebot_plugin_orm import Model
from nonebot_plugin_saa import PlatformTarget
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column


class MorningGreeting(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    target: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))

    @property
    def saa_target(self) -> PlatformTarget:
        return PlatformTarget.deserialize(self.target)
