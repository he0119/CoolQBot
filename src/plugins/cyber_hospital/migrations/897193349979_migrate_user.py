"""migrate user

Revision ID: 897193349979
Revises: c2363e778e1c
Create Date: 2023-09-18 15:58:17.052495

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision = "897193349979"
down_revision = "c2363e778e1c"
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

    Patient = Base.classes.cyber_hospital_patient
    User = Base.classes.nonebot_plugin_user_user
    Bind = Base.classes.nonebot_plugin_user_bind
    with Session(op.get_bind()) as session:
        patients = session.scalars(sa.select(Patient)).all()
        for patient in patients:
            user_id = create_user(User, Bind, "qq", patient.user_id)
            patient.new_user_id = user_id
            patient.new_group_id = f"qq_{patient.group_id}"
            session.add(patient)
        session.commit()


def downgrade() -> None:
    pass
