from typing import cast

from nonebot_plugin_datastore import create_session
from sqlalchemy.orm import selectinload
from sqlmodel import select

from .model import Patient, Record


class Hospital:
    async def admit_patient(self, user_id: str, group_id: str) -> None:
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

            patient = Patient(user_id=user_id, group_id=group_id)
            session.add(patient)
            await session.commit()

    async def discharge_patient(self, user_id: str, group_id: str) -> None:
        async with create_session() as session:
            statement = (
                select(Patient)
                .where(Patient.user_id == user_id)
                .where(Patient.group_id == group_id)
                .where(Patient.discharged_at == None)
            )
            results = await session.exec(statement)  # type: ignore
            patient = results.first()  # type: ignore
            if patient is None:
                raise ValueError("病人未入院")

            patient.discharge()
            session.add(patient)
            await session.commit()

    async def get_patients(self, group_id: str) -> list[Patient]:
        async with create_session() as session:
            statement = (
                select(Patient)
                .where(Patient.group_id == group_id)
                .where(Patient.discharged_at == None)
            )
            results = await session.exec(statement)  # type: ignore
            return results.all()  # type: ignore

    async def get_patient(self, user_id: str, group_id: str) -> Patient | None:
        async with create_session() as session:
            statement = (
                select(Patient)
                .where(Patient.user_id == user_id)
                .where(Patient.group_id == group_id)
                .where(Patient.discharged_at == None)
            )
            results = await session.exec(statement)  # type: ignore
            return results.first()

    async def get_records(self, user_id: str, group_id: str) -> list[Record] | None:
        async with create_session() as session:
            statement = (
                select(Patient)
                .where(Patient.user_id == user_id)
                .where(Patient.group_id == group_id)
                .where(Patient.discharged_at == None)
            ).options(selectinload(Patient.records))
            results = await session.exec(statement)  # type: ignore
            patient = results.first()
            if patient is None:
                raise ValueError("病人未入院")
            patient = cast(Patient, patient)
            return patient.records

    async def add_record(self, user_id: str, group_id: str, content: str) -> None:
        async with create_session() as session:
            statement = (
                select(Patient)
                .where(Patient.user_id == user_id)
                .where(Patient.group_id == group_id)
                .where(Patient.discharged_at == None)
            )
            results = await session.exec(statement)  # type: ignore
            patient = results.first()
            if patient is None:
                raise ValueError("病人未入院")

            patient = cast(Patient, patient)
            record = Record(content=content, patient=patient)
            session.add(record)
            await session.commit()
