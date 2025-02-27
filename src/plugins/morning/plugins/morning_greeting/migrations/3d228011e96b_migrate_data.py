"""migrate data

修订 ID: 3d228011e96b
父修订: 65a94a4a643b
创建时间: 2023-10-29 18:41:38.769018

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

revision: str = "3d228011e96b"
down_revision: str | Sequence[str] | None = "65a94a4a643b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _migrate_old_data(ds_conn: Connection):
    insp = inspect(ds_conn)
    if (
        "morning_greeting_morninggreeting" not in insp.get_table_names()
        or "morning_greeting_alembic_version" not in insp.get_table_names()
    ):
        logger.info("morning_greeting: 未发现来自 datastore 的数据")
        return

    DsBase = automap_base()
    DsBase.prepare(autoload_with=ds_conn)
    ds_session = Session(ds_conn)

    AlembicVersion = DsBase.classes.morning_greeting_alembic_version
    version_num = ds_session.scalars(select(AlembicVersion.version_num)).one_or_none()
    if not version_num:
        return
    if version_num != "1739ad88af26":
        logger.warning(
            "morning_greeting: 发现旧版本的数据，请先安装 0.16.1 版本，"
            "并运行 nb datastore upgrade 完成数据迁移之后再安装新版本"
        )
        raise RuntimeError("morning_greeting: 请先安装 0.16.1 版本完成迁移之后再升级")

    DsMorningGreeting = DsBase.classes.morning_greeting_morninggreeting

    Base = automap_base()
    Base.prepare(autoload_with=op.get_bind())
    session = Session(op.get_bind())

    MorningGreeting = Base.classes.morning_greeting_morninggreeting

    # 写入数据
    logger.info("morning_greeting: 发现来自 datastore 的数据，正在迁移...")
    for ds_morning_greeting in ds_session.query(DsMorningGreeting).all():
        morning_greeting = MorningGreeting(
            id=ds_morning_greeting.id,
            target=ds_morning_greeting.target,
        )
        session.add(morning_greeting)

    session.commit()
    logger.info("morning_greeting: 迁移完成")


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
