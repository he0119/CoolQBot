from datetime import datetime

from nonebot_plugin_datastore import get_plugin_data
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

Model = get_plugin_data().Model


class User(Model):
    """用户"""

    __table_args__ = (UniqueConstraint("platform", "user_id", name="unique-user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[str] = mapped_column(String(64))

    target_weight: Mapped[float | None]
    target_body_fat: Mapped[float | None]

    fitness_records: Mapped[list["FitnessRecord"]] = relationship(back_populates="user")
    dietary_records: Mapped[list["DietaryRecord"]] = relationship(back_populates="user")
    weight_records: Mapped[list["WeightRecord"]] = relationship(back_populates="user")
    body_fat_records: Mapped[list["BodyFatRecord"]] = relationship(
        back_populates="user"
    )


class FitnessRecord(Model):
    """健身记录"""

    id: Mapped[int] = mapped_column(primary_key=True)
    time: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    message: Mapped[str] = mapped_column(Text)

    user_id: Mapped[int] = mapped_column(ForeignKey("check_in_user.id"))
    user: Mapped[User] = relationship(back_populates="fitness_records")


class DietaryRecord(Model):
    """饮食记录"""

    id: Mapped[int] = mapped_column(primary_key=True)
    time: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    healthy: Mapped[bool]

    user_id: Mapped[int] = mapped_column(ForeignKey("check_in_user.id"))
    user: Mapped[User] = relationship(back_populates="dietary_records")


class WeightRecord(Model):
    """体重记录"""

    id: Mapped[int] = mapped_column(primary_key=True)
    time: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    weight: Mapped[float]

    user_id: Mapped[int] = mapped_column(ForeignKey("check_in_user.id"))
    user: Mapped[User] = relationship(back_populates="weight_records")


class BodyFatRecord(Model):
    """体脂记录"""

    id: Mapped[int] = mapped_column(primary_key=True)
    time: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    body_fat: Mapped[float]

    user_id: Mapped[int] = mapped_column(ForeignKey("check_in_user.id"))
    user: Mapped[User] = relationship(back_populates="body_fat_records")
