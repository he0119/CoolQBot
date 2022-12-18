from typing import Optional

from nonebot_plugin_datastore import create_session
from sqlmodel import select

from .model import Patient, Record


class Hospital:
    async def admit_patient(self, user_id: str) -> None:
        async with create_session() as session:
            statement = (
                select(Patient)
                .where(Patient.user_id == user_id)
                .where(Patient.discharged_at == None)
            )
            results = await session.exec(statement)  # type: ignore
            patient = results.first()  # type: ignore
            if patient is not None:
                raise ValueError("病人已入院")

            patient = Patient(user_id=user_id)
            session.add(patient)
            await session.commit()

    async def discharge_patient(self, user_id: str) -> None:
        async with create_session() as session:
            statement = (
                select(Patient)
                .where(Patient.user_id == user_id)
                .where(Patient.discharged_at == None)
            )
            results = await session.exec(statement)  # type: ignore
            patient = results.first()  # type: ignore
            if patient is None:
                raise ValueError("病人未入院")

            patient.discharge()
            session.add(patient)
            await session.commit()

    async def get_patients(self) -> list[Patient]:
        async with create_session() as session:
            statement = select(Patient).where(Patient.discharged_at == None)
            results = await session.exec(statement)  # type: ignore
            return results.all()  # type: ignore
