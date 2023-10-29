from datetime import datetime

from nonebot_plugin_orm import Model
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column


class UserInfo(Model):
    """用户信息"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    target_weight: Mapped[float | None]
    target_body_fat: Mapped[float | None]


class FitnessRecord(Model):
    """健身记录"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    time: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    message: Mapped[str] = mapped_column(Text)


class DietaryRecord(Model):
    """饮食记录"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    time: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    healthy: Mapped[bool]


class WeightRecord(Model):
    """体重记录"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    time: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    weight: Mapped[float]


class BodyFatRecord(Model):
    """体脂记录"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    time: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    body_fat: Mapped[float]
