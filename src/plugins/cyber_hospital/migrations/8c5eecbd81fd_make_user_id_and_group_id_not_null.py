"""make user_id and group_id not null

Revision ID: 8c5eecbd81fd
Revises: c9cd5d567291
Create Date: 2023-09-18 16:07:40.929389

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8c5eecbd81fd"
down_revision = "c9cd5d567291"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("cyber_hospital_patient", schema=None) as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=False)
        batch_op.alter_column("group_id", existing_type=sa.VARCHAR(), nullable=False)

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("cyber_hospital_patient", schema=None) as batch_op:
        batch_op.alter_column("group_id", existing_type=sa.VARCHAR(), nullable=True)
        batch_op.alter_column("user_id", existing_type=sa.INTEGER(), nullable=True)

    # ### end Alembic commands ###
