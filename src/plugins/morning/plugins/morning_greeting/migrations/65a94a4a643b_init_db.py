"""init db

修订 ID: 65a94a4a643b
父修订:
创建时间: 2023-10-29 11:34:30.658512

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "65a94a4a643b"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = ("morning_greeting",)
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "morning_greeting_morninggreeting",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "target",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_morning_greeting_morninggreeting")),
        info={"bind_key": "morning_greeting"},
    )
    # ### end Alembic commands ###


def downgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("morning_greeting_morninggreeting")
    # ### end Alembic commands ###
