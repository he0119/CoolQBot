"""init db

修订 ID: c3c52d7c9d07
父修订:
创建时间: 2023-10-29 11:30:46.197157

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "c3c52d7c9d07"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = ("ff14_fflogs",)
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "ff14_fflogs_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("character_name", sa.String(), nullable=False),
        sa.Column("server_name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ff14_fflogs_user")),
        info={"bind_key": "ff14_fflogs"},
    )
    with op.batch_alter_table("ff14_fflogs_user", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ff14_fflogs_user_user_id"), ["user_id"], unique=True)

    # ### end Alembic commands ###


def downgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("ff14_fflogs_user", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ff14_fflogs_user_user_id"))

    op.drop_table("ff14_fflogs_user")
    # ### end Alembic commands ###
