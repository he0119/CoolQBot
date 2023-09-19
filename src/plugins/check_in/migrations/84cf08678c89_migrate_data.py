"""migrate data

Revision ID: 84cf08678c89
Revises: 97641dfc009c
Create Date: 2023-09-15 12:27:54.294599

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision = "84cf08678c89"
down_revision = "97641dfc009c"
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

    OldUser = Base.classes.check_in_user
    UserInfo = Base.classes.check_in_userinfo
    User = Base.classes.user_user
    Bind = Base.classes.user_bind
    user_id_map = {}
    with Session(op.get_bind()) as session:
        users = session.scalars(sa.select(OldUser)).all()
        for user in users:
            user_id_map[user.id] = {
                "platform": user.platform,
                "pid": user.user_id,
            }
            uid = create_user(User, Bind, user.platform, user.user_id)
            user_info = UserInfo(
                user_id=uid,
                target_weight=user.target_weight,
                target_body_fat=user.target_body_fat,
            )
            session.add(user_info)
        session.commit()

    FitnessRecord = Base.classes.check_in_fitnessrecord
    FitnessRecordTemp = Base.classes.check_in_fitnessrecord_temp
    with Session(op.get_bind()) as session:
        records = session.scalars(sa.select(FitnessRecord)).all()
        for record in records:
            uid = create_user(User, Bind, **user_id_map[record.user_id])
            record_temp = FitnessRecordTemp(
                user_id=uid,
                time=record.time,
                message=record.message,
            )
            session.add(record_temp)
        session.commit()

    DietaryRecord = Base.classes.check_in_dietaryrecord
    DietaryRecordTemp = Base.classes.check_in_dietaryrecord_temp
    with Session(op.get_bind()) as session:
        records = session.scalars(sa.select(DietaryRecord)).all()
        for record in records:
            uid = create_user(User, Bind, **user_id_map[record.user_id])
            record_temp = DietaryRecordTemp(
                user_id=uid,
                time=record.time,
                healthy=record.healthy,
            )
            session.add(record_temp)
        session.commit()

    WeightRecord = Base.classes.check_in_weightrecord
    WeightRecordTemp = Base.classes.check_in_weightrecord_temp
    with Session(op.get_bind()) as session:
        records = session.scalars(sa.select(WeightRecord)).all()
        for record in records:
            uid = create_user(User, Bind, **user_id_map[record.user_id])
            record_temp = WeightRecordTemp(
                user_id=uid,
                time=record.time,
                weight=record.weight,
            )
            session.add(record_temp)
        session.commit()

    BodyFatRecord = Base.classes.check_in_bodyfatrecord
    BodyFatRecordTemp = Base.classes.check_in_bodyfatrecord_temp
    with Session(op.get_bind()) as session:
        records = session.scalars(sa.select(BodyFatRecord)).all()
        for record in records:
            uid = create_user(User, Bind, **user_id_map[record.user_id])
            record_temp = BodyFatRecordTemp(
                user_id=uid,
                time=record.time,
                body_fat=record.body_fat,
            )
            session.add(record_temp)
        session.commit()


def downgrade() -> None:
    pass
