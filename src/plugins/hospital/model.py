from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class Patient(SQLModel, table=True):
    """病人"""

    __tablename__: str = "cyber_hospital_patient"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    user_id: str
    records: list["Record"] | None = Relationship(back_populates="patient")
    admitted_at: datetime = Field(default_factory=datetime.now)
    discharged_at: datetime | None = None

    def discharge(self) -> None:
        self.discharged_at = datetime.now()


class Record(SQLModel, table=True):
    """病历"""

    __tablename__: str = "cyber_hospital_record"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    patient: Patient | None = Relationship(back_populates="records")
    patient_id: int | None = Field(
        default=None, foreign_key="cyber_hospital_patient.id"
    )
    time: datetime = Field(default_factory=datetime.now)
    content: str
