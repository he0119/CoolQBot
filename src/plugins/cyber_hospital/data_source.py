# ruff: noqa: E711
from collections.abc import Sequence

from nonebot_plugin_orm import get_session
from sqlalchemy import Row, func, select
from sqlalchemy.orm import selectinload

from .model import Patient, Record


class Hospital:
    async def admit_patient(self, user_id: int, group_id: str) -> None:
        async with get_session() as session:
            statement = (
                select(Patient)
                .where(Patient.user_id == user_id)
                .where(Patient.group_id == group_id)
                .where(Patient.discharged_at == None)
            )
            results = await session.scalars(statement)
            patient = results.first()
            if patient is not None:
                raise ValueError("病人已入院")

            patient = Patient(user_id=user_id, group_id=group_id)
            session.add(patient)
            await session.commit()

    async def discharge_patient(self, user_id: int, group_id: str) -> None:
        async with get_session() as session:
            statement = (
                select(Patient)
                .where(Patient.user_id == user_id)
                .where(Patient.group_id == group_id)
                .where(Patient.discharged_at == None)
            )
            results = await session.scalars(statement)
            patient = results.first()
            if patient is None:
                raise ValueError("病人未入院")

            patient.discharge()
            session.add(patient)
            await session.commit()

    async def get_admitted_patients(self, group_id: str) -> Sequence[Patient]:
        """获取所有入院病人"""
        async with get_session() as session:
            statement = (
                select(Patient).where(Patient.group_id == group_id).where(Patient.discharged_at == None)
            ).options(selectinload(Patient.records))
            results = await session.scalars(statement)
            return results.all()

    async def get_admitted_patient(self, uid: int) -> Patient | None:
        """获取入院病人"""
        async with get_session() as session:
            statement = select(Patient).where(Patient.user_id == uid).where(Patient.discharged_at == None)
            results = await session.scalars(statement)
            return results.first()

    async def get_records(self, user_id: int, group_id: str) -> list[Record] | None:
        async with get_session() as session:
            statement = (
                select(Patient)
                .where(Patient.user_id == user_id)
                .where(Patient.group_id == group_id)
                .where(Patient.discharged_at == None)
            ).options(selectinload(Patient.records))
            results = await session.scalars(statement)
            patient = results.first()
            if patient is None:
                raise ValueError("病人未入院")
            return patient.records

    async def add_record(self, uid: int, content: str) -> None:
        async with get_session() as session:
            statement = select(Patient).where(Patient.user_id == uid).where(Patient.discharged_at == None)
            results = await session.scalars(statement)
            patient = results.first()
            if patient is None:
                raise ValueError("病人未入院")

            record = Record(content=content, patient=patient)
            session.add(record)
            await session.commit()

    async def patient_count(self, group_id: str) -> Sequence[Row[tuple[int, int]]]:
        """统计病人住院次数"""
        async with get_session() as session:
            statement = (
                select(Patient.user_id, func.count(Patient.user_id))
                .group_by(Patient.user_id)
                .where(Patient.group_id == group_id)
            )
            results = (await session.execute(statement)).all()
            return results

    async def get_patient(self, user_id: int, group_id: str) -> Sequence[Patient]:
        """获取病人所有住院记录"""
        async with get_session() as session:
            statement = select(Patient).where(Patient.user_id == user_id).where(Patient.group_id == group_id)
            results = await session.scalars(statement)
            return results.all()
