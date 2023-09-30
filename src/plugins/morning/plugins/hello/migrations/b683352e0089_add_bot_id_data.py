"""add bot_id data

Revision ID: b683352e0089
Revises: 371e102dcdb9
Create Date: 2023-09-30 08:46:28.829111

"""
import sqlalchemy as sa
from alembic import op
from nonebot import get_driver
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision = "b683352e0089"
down_revision = "371e102dcdb9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base = automap_base()
    Base.prepare(autoload_with=op.get_bind())
    Hello = Base.classes.hello_hello
    config = get_driver().config
    migration_bot_id = getattr(config, "migration_bot_id", None)
    with Session(op.get_bind()) as session:
        hellos = session.scalars(sa.select(Hello)).all()
        if hellos and migration_bot_id is None:
            raise ValueError("你需要设置 migration_bot_id 以完成迁移")

        for hello in hellos:
            hello.bot_id = migration_bot_id
        session.commit()


def downgrade() -> None:
    pass
