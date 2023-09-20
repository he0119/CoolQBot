"""drop columns

Revision ID: 9149f07d54a1
Revises: 3a877255661e
Create Date: 2023-09-16 15:39:58.957890

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9149f07d54a1"
down_revision = "3a877255661e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("ff14_fflogs_user", schema=None) as batch_op:
        batch_op.alter_column("user", existing_type=sa.INTEGER(), nullable=False)
        batch_op.drop_column("platform")
        batch_op.drop_column("user_id")

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("ff14_fflogs_user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.VARCHAR(), nullable=False))
        batch_op.add_column(sa.Column("platform", sa.VARCHAR(), nullable=False))
        batch_op.alter_column("user", existing_type=sa.INTEGER(), nullable=True)

    # ### end Alembic commands ###