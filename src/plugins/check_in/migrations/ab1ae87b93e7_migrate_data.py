"""migrate data

修订 ID: ab1ae87b93e7
父修订: 41333e58f5eb
创建时间: 2023-10-29 18:24:16.625405

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
from nonebot import logger
from sqlalchemy import Connection, inspect, select
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncConnection

revision: str = "ab1ae87b93e7"
down_revision: str | Sequence[str] | None = "41333e58f5eb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _migrate_old_data(ds_conn: Connection):
    insp = inspect(ds_conn)
    if "check_in_userinfo" not in insp.get_table_names() or "check_in_alembic_version" not in insp.get_table_names():
        logger.info("check_in: 未发现来自 datastore 的数据")
        return

    DsBase = automap_base()
    DsBase.prepare(autoload_with=ds_conn)
    ds_session = Session(ds_conn)

    AlembicVersion = DsBase.classes.check_in_alembic_version
    version_num = ds_session.scalars(select(AlembicVersion.version_num)).one_or_none()
    if not version_num:
        return
    if version_num != "6c3d023e73d4":
        logger.warning(
            "check_in: 发现旧版本的数据，请先安装 0.16.1 版本，并运行 nb datastore upgrade 完成数据迁移之后再安装新版本"
        )
        raise RuntimeError("check_in: 请先安装 0.16.1 版本完成迁移之后再升级")

    DsUserInfo = DsBase.classes.check_in_userinfo
    DsFitnessRecord = DsBase.classes.check_in_fitnessrecord
    DsDietaryRecord = DsBase.classes.check_in_dietaryrecord
    DsWeightRecord = DsBase.classes.check_in_weightrecord
    DsBodyFatRecord = DsBase.classes.check_in_bodyfatrecord

    Base = automap_base()
    Base.prepare(autoload_with=op.get_bind())
    session = Session(op.get_bind())

    UserInfo = Base.classes.check_in_userinfo
    FitnessRecord = Base.classes.check_in_fitnessrecord
    DietaryRecord = Base.classes.check_in_dietaryrecord
    WeightRecord = Base.classes.check_in_weightrecord
    BodyFatRecord = Base.classes.check_in_bodyfatrecord

    # 写入数据
    logger.info("check_in: 发现来自 datastore 的数据，正在迁移...")
    for ds_user_info in ds_session.query(DsUserInfo).all():
        user = UserInfo(
            id=ds_user_info.id,
            user_id=ds_user_info.user_id,
            target_weight=ds_user_info.target_weight,
            target_body_fat=ds_user_info.target_body_fat,
        )
        session.add(user)
    for ds_fitness_record in ds_session.query(DsFitnessRecord).all():
        fitness_record = FitnessRecord(
            id=ds_fitness_record.id,
            user_id=ds_fitness_record.user_id,
            time=ds_fitness_record.time,
            message=ds_fitness_record.message,
        )
        session.add(fitness_record)
    for ds_dietary_record in ds_session.query(DsDietaryRecord).all():
        dietary_record = DietaryRecord(
            id=ds_dietary_record.id,
            user_id=ds_dietary_record.user_id,
            time=ds_dietary_record.time,
            healthy=ds_dietary_record.healthy,
        )
        session.add(dietary_record)
    for ds_weight_record in ds_session.query(DsWeightRecord).all():
        weight_record = WeightRecord(
            id=ds_weight_record.id,
            user_id=ds_weight_record.user_id,
            time=ds_weight_record.time,
            weight=ds_weight_record.weight,
        )
        session.add(weight_record)
    for ds_body_fat_record in ds_session.query(DsBodyFatRecord).all():
        body_fat_record = BodyFatRecord(
            id=ds_body_fat_record.id,
            user_id=ds_body_fat_record.user_id,
            time=ds_body_fat_record.time,
            body_fat=ds_body_fat_record.body_fat,
        )
        session.add(body_fat_record)

    session.commit()
    logger.info("check_in: 迁移完成")


async def data_migrate(conn: AsyncConnection):
    from nonebot_plugin_datastore.db import get_engine

    async with get_engine().connect() as ds_conn:
        await ds_conn.run_sync(_migrate_old_data)


def upgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.run_async(data_migrate)
    # ### end Alembic commands ###


def downgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
