"""init db

Revision ID: 260e463af484
Revises:
Create Date: 2023-03-05 12:07:52.167701

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "260e463af484"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "hello_hello",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=True),
        sa.Column("guild_id", sa.String(), nullable=True),
        sa.Column("channel_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "platform", "group_id", "guild_id", "channel_id", name="unique_hello"
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("hello_hello")
    # ### end Alembic commands ###
