"""migrate data

Revision ID: 3a877255661e
Revises: fa09d8974213
Create Date: 2023-09-16 15:33:22.272696

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision = "3a877255661e"
down_revision = "fa09d8974213"
branch_labels = None
depends_on = None


def create_user(User, Bind, platform: str, pid: str):
    with Session(op.get_bind()) as session:
        bind = (
            session.scalars(
                sa.select(Bind).where(Bind.pid == pid).where(Bind.platform == platform)
            )
        ).one_or_none()

        if not bind:
            user = User(name=pid, created_at=sa.func.now())
            session.add(user)
            session.commit()
            session.refresh(user)
            bind = Bind(
                pid=pid,
                platform=platform,
                aid=user.id,
                bid=user.id,
            )
            session.add(bind)
            session.commit()
            return user.id

        return bind.aid


def upgrade() -> None:
    Base = automap_base()
    Base.prepare(op.get_bind())

    FF14User = Base.classes.ff14_fflogs_user
    User = Base.classes.user_user
    Bind = Base.classes.user_bind
    with Session(op.get_bind()) as session:
        users = session.scalars(sa.select(FF14User)).all()
        for user in users:
            uid = create_user(User, Bind, user.platform, user.user_id)
            user.user = uid
        session.commit()


def downgrade() -> None:
    pass
