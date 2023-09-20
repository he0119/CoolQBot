"""make target non-nullable

Revision ID: 1739ad88af26
Revises: e3ce6ed12f34
Create Date: 2023-09-19 10:53:09.060765

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "1739ad88af26"
down_revision = "e3ce6ed12f34"
branch_labels = None
depends_on = None


def jsonb_if_postgresql_else_json():
    return sa.JSON().with_variant(JSONB, "postgresql")


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table(
        "morning_greeting_morninggreeting", schema=None
    ) as batch_op:
        batch_op.alter_column(
            "target",
            existing_type=jsonb_if_postgresql_else_json(),
            nullable=False,
        )

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table(
        "morning_greeting_morninggreeting", schema=None
    ) as batch_op:
        batch_op.alter_column(
            "target",
            existing_type=jsonb_if_postgresql_else_json(),
            nullable=True,
        )

    # ### end Alembic commands ###