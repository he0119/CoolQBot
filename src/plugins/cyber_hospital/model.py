from datetime import datetime

from nonebot_plugin_datastore import get_plugin_data
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

Model = get_plugin_data().Model


class Patient(Model):
    """病人"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    group_id: Mapped[str]
    records: Mapped[list["Record"]] = relationship(back_populates="patient")
    admitted_at: Mapped[datetime] = mapped_column(default=datetime.now)
    discharged_at: Mapped[datetime | None]

    def discharge(self) -> None:
        self.discharged_at = datetime.now()


class Record(Model):
    """病历"""

    id: Mapped[int] = mapped_column(primary_key=True)
    patient: Mapped[Patient] = relationship(back_populates="records")
    patient_id: Mapped[int] = mapped_column(ForeignKey("cyber_hospital_patient.id"))
    time: Mapped[datetime] = mapped_column(default=datetime.now)
    content: Mapped[str]
