"""fix user_id type

修订 ID: 475c80e93acc
父修订: ab1ae87b93e7
创建时间: 2023-10-29 19:48:38.555866

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "475c80e93acc"
down_revision: str | Sequence[str] | None = "ab1ae87b93e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("cyber_hospital_patient", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.VARCHAR(),
            type_=sa.Integer(),
            existing_nullable=False,
        )

    # ### end Alembic commands ###


def downgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("cyber_hospital_patient", schema=None) as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            type_=sa.VARCHAR(),
            existing_nullable=False,
        )

    # ### end Alembic commands ###