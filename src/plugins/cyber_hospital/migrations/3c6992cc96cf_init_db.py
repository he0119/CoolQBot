"""init db

修订 ID: 3c6992cc96cf
父修订: ac57f7074e58
创建时间: 2023-10-29 11:28:42.658746

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3c6992cc96cf"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = ("cyber_hospital",)
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "cyber_hospital_patient",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("admitted_at", sa.DateTime(), nullable=False),
        sa.Column("discharged_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cyber_hospital_patient")),
        info={"bind_key": "cyber_hospital"},
    )
    op.create_table(
        "cyber_hospital_record",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["cyber_hospital_patient.id"],
            name=op.f("fk_cyber_hospital_record_patient_id_cyber_hospital_patient"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cyber_hospital_record")),
        info={"bind_key": "cyber_hospital"},
    )
    # ### end Alembic commands ###


def downgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("cyber_hospital_record")
    op.drop_table("cyber_hospital_patient")
    # ### end Alembic commands ###
