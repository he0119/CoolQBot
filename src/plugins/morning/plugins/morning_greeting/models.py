from nonebot_plugin_datastore import get_plugin_data
from nonebot_plugin_saa import PlatformTarget
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

Model = get_plugin_data().Model


class MorningGreeting(MappedAsDataclass, Model):
    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    target: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"))

    @property
    def saa_target(self) -> PlatformTarget:
        return PlatformTarget.deserialize(self.target)
