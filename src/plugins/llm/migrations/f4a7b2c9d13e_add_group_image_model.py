"""add group image model

迁移 ID: f4a7b2c9d13e
父迁移: 8c2d7e4f91ab
创建时间: 2026-11-05 23:20:00

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "f4a7b2c9d13e"
down_revision: str | Sequence[str] | None = "8c2d7e4f91ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    with op.batch_alter_table("llm_groupllmconfig", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image_model", sa.String(), nullable=True))


def downgrade(name: str = "") -> None:
    if name:
        return
    with op.batch_alter_table("llm_groupllmconfig", schema=None) as batch_op:
        batch_op.drop_column("image_model")
