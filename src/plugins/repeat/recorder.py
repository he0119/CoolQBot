"""数据记录

记录排行版，历史，状态所需的数据
如果遇到老版本数据，则自动升级
"""

from datetime import date, datetime, timedelta
from functools import cache

from nonebot_plugin_datastore import get_plugin_data
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from .models import Enabled, MessageRecord

plugin_data = get_plugin_data()


@cache
def get_recorder(session_id: str) -> "Recorder":
    """获取 Recorder 实例的工厂函数，使用 cache 实现单例模式"""
    return Recorder(session_id)


class Recorder:
    def __init__(self, session_id: str):
        self._msg_send_time: list[datetime] = []
        self._last_message_on: datetime = datetime.now()

        self.session_id = session_id

    def message_number(self, x: int):
        """返回指定群 x 分钟内的消息条数，并清除之前的消息记录"""

        now = datetime.now()
        for i in range(len(self._msg_send_time)):
            if self._msg_send_time[i] > now - timedelta(minutes=x):
                self._msg_send_time = self._msg_send_time[i:]
                return len(self._msg_send_time)

        # 如果没有满足条件的消息，则清除记录
        self._msg_send_time.clear()
        return 0

    async def get_records(self, year: int | None = None, month: int | None = None):
        """获取指定月的复读记录

        没有参数则为当月数据
        只填写年月为这个月的数据
        """
        if year is None and month is None:
            end = datetime.now().date()
            start = end.replace(day=1)
        else:
            if year is None:
                raise ValueError("year 不能为 None")
            if month is None:
                raise ValueError("month 不能为 None")
            if month != 12:
                end = date(year, month + 1, 1) - timedelta(days=1)
            else:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            start = date(year, month, 1)

        async with get_session() as session:
            records = await session.execute(
                select(MessageRecord)
                .where(MessageRecord.session_id == self.session_id)
                .where(MessageRecord.date >= start)
                .where(MessageRecord.date <= end)
            )
            return records.scalars().all()

    async def get_records_by_day(self, year: int, month: int, day: int):
        """获取指定群某一天的复读记录

        只填写日为这个月第几日的数据
        """
        time = date(year, month, day)
        async with get_session() as session:
            records = await session.execute(
                select(MessageRecord)
                .where(MessageRecord.session_id == self.session_id)
                .where(MessageRecord.date == time)
            )
            return records.scalars().all()

    async def add_repeat_list(self, user_id: int):
        """该 QQ 号在指定群的复读记录，加一"""
        now_date = datetime.now().date()
        async with get_session() as session:
            record = await session.scalar(
                select(MessageRecord)
                .where(MessageRecord.date == now_date)
                .where(MessageRecord.uid == user_id)
                .where(MessageRecord.session_id == self.session_id)
            )
            if record:
                record.msg_number += 1
                record.repeat_time += 1
                await session.commit()
            else:
                record = MessageRecord(
                    date=now_date,
                    uid=user_id,
                    msg_number=1,
                    repeat_time=1,
                    session_id=self.session_id,
                )
                session.add(record)
                await session.commit()

    async def add_msg_number_list(self, user_id: int):
        """该 QQ 号在指定群的消息数量记录，加一"""
        now_date = datetime.now().date()
        async with get_session() as session:
            record = await session.scalar(
                select(MessageRecord)
                .where(MessageRecord.date == now_date)
                .where(MessageRecord.uid == user_id)
                .where(MessageRecord.session_id == self.session_id)
            )
            if record:
                record.msg_number += 1
                await session.commit()
            else:
                record = MessageRecord(
                    date=now_date,
                    uid=user_id,
                    msg_number=1,
                    session_id=self.session_id,
                )
                session.add(record)
                await session.commit()

    def add_msg_send_time(self, time):
        """将这个时间加入到指定群的消息发送时间列表中"""
        self._msg_send_time.append(time)

    def last_message_on(self):
        return self._last_message_on

    def reset_last_message_on(self):
        self._last_message_on = datetime.now()

    async def is_enabled(self):
        async with get_session() as session:
            return (await session.scalars(select(Enabled).where(Enabled.session_id == self.session_id))).one_or_none()
