"""add group model settings

迁移 ID: 8c2d7e4f91ab
父迁移: 0cc75f2d06b0
创建时间: 2026-08-03 19:20:00

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "8c2d7e4f91ab"
down_revision: str | Sequence[str] | None = "0cc75f2d06b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    with op.batch_alter_table("llm_groupllmconfig", schema=None) as batch_op:
        batch_op.add_column(sa.Column("available_models", sa.JSON(none_as_null=True), nullable=True))
        batch_op.add_column(sa.Column("zssm_model", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("zssm_vision_model", sa.String(), nullable=True))


def downgrade(name: str = "") -> None:
    if name:
        return
    with op.batch_alter_table("llm_groupllmconfig", schema=None) as batch_op:
        batch_op.drop_column("zssm_vision_model")
        batch_op.drop_column("zssm_model")
        batch_op.drop_column("available_models")
