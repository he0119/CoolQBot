"""数据记录

记录排行版，历史，状态所需的数据
如果遇到老版本数据，则自动升级
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from nonebot import get_driver, get_plugin_config
from nonebot.log import logger
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from .config import Config
from .models import Enabled, MessageRecord

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.utils.annotated import AsyncSession

plugin_config = get_plugin_config(Config)


driver = get_driver()


@dataclass
class PendingStat:
    msg_number: int = 0
    repeat_time: int = 0


_RECORDER_REGISTRY: dict[str, Recorder] = {}
_FLUSH_TASK: asyncio.Task[Any] | None = None


async def flush_all_recorders() -> None:
    """Flush buffered stats for every recorder instance."""

    if not _RECORDER_REGISTRY:
        return

    results = await asyncio.gather(
        *(recorder.flush() for recorder in _RECORDER_REGISTRY.values()),
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, Exception):
            logger.opt(exception=result).warning("Failed to flush repeat statistics")


async def _flush_worker() -> None:
    try:
        while True:
            await asyncio.sleep(max(plugin_config.repeat_flush_interval, 1))
            await flush_all_recorders()
    except asyncio.CancelledError:
        raise


@driver.on_startup
async def _start_repeat_flush_task() -> None:
    global _FLUSH_TASK

    if plugin_config.repeat_flush_interval <= 0:
        return

    if _FLUSH_TASK is None or _FLUSH_TASK.done():
        _FLUSH_TASK = asyncio.create_task(_flush_worker())


@driver.on_shutdown
async def _stop_repeat_flush_task() -> None:
    global _FLUSH_TASK

    if _FLUSH_TASK:
        _FLUSH_TASK.cancel()
        with suppress(asyncio.CancelledError):
            await _FLUSH_TASK
        _FLUSH_TASK = None

    await flush_all_recorders()


def get_recorder(session_id: str) -> Recorder:
    """获取 Recorder 实例的工厂函数,使用 registry 实现单例模式"""
    if session_id not in _RECORDER_REGISTRY:
        recorder = Recorder(session_id)
        _RECORDER_REGISTRY[recorder.session_id] = recorder
    return _RECORDER_REGISTRY[session_id]


class Recorder:
    def __init__(self, session_id: str) -> None:
        self._msg_send_time: list[datetime] = []
        self._last_message_on: datetime = datetime.now()

        self.session_id = session_id
        self._pending_stats: dict[tuple[date, int], PendingStat] = {}
        self._pending_lock = asyncio.Lock()
        self._flush_lock = asyncio.Lock()
        self._pending_events = 0
        self._flush_task: asyncio.Task[Any] | None = None
        self._enabled: bool | None = None

    async def is_enabled(self) -> bool:
        """该群是否开启复读功能"""
        if self._enabled is not None:
            return self._enabled

        async with get_session() as session:
            enabled = bool(
                (await session.scalars(select(Enabled).where(Enabled.session_id == self.session_id))).one_or_none()
            )

        self._enabled = enabled
        return enabled

    async def enable(self, session: AsyncSession):
        """开启复读功能"""
        record = await session.scalars(select(Enabled).where(Enabled.session_id == self.session_id))
        group = record.one_or_none()
        if not group:
            session.add(Enabled(session_id=self.session_id))
            await session.commit()
        self._enabled = True

    async def disable(self, session: AsyncSession):
        """关闭复读功能"""
        record = await session.scalars(select(Enabled).where(Enabled.session_id == self.session_id))
        enabled = record.one_or_none()
        if enabled:
            await session.delete(enabled)
            await session.commit()
        self._enabled = False

    def message_number(self, x: int) -> int:
        """返回指定群 x 分钟内的消息条数，并清除之前的消息记录"""

        now = datetime.now()
        for i in range(len(self._msg_send_time)):
            if self._msg_send_time[i] > now - timedelta(minutes=x):
                self._msg_send_time = self._msg_send_time[i:]
                return len(self._msg_send_time)

        # 如果没有满足条件的消息，则清除记录
        self._msg_send_time.clear()
        return 0

    async def get_records(self, year: int | None = None, month: int | None = None) -> Sequence[MessageRecord]:
        """获取指定月的复读记录

        没有参数则为当月数据
        只填写年月为这个月的数据
        """
        await self.flush()

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

    async def get_records_by_day(self, year: int, month: int, day: int) -> Sequence[MessageRecord]:
        """获取指定群某一天的复读记录

        只填写日为这个月第几日的数据
        """
        time = date(year, month, day)
        await self.flush()
        async with get_session() as session:
            records = await session.execute(
                select(MessageRecord)
                .where(MessageRecord.session_id == self.session_id)
                .where(MessageRecord.date == time)
            )
            return records.scalars().all()

    async def add_repeat_list(self, user_id: int) -> None:
        """该 QQ 号在指定群的复读记录，加一"""
        await self._record_stat(user_id, msg_delta=1, repeat_delta=1)

    async def add_msg_number_list(self, user_id: int) -> None:
        """该 QQ 号在指定群的消息数量记录，加一"""
        await self._record_stat(user_id, msg_delta=1, repeat_delta=0)

    def add_msg_send_time(self, time: datetime) -> None:
        """将这个时间加入到指定群的消息发送时间列表中"""
        self._msg_send_time.append(time)

    def last_message_on(self) -> datetime:
        return self._last_message_on

    def reset_last_message_on(self) -> None:
        self._last_message_on = datetime.now()

    async def flush(self) -> None:
        task = self._flush_task
        if task and not task.done():
            await task
            return

        new_task = asyncio.create_task(self._execute_flush())
        self._attach_flush_task(new_task)
        await new_task

    async def _record_stat(self, user_id: int, msg_delta: int, repeat_delta: int) -> None:
        if msg_delta == 0 and repeat_delta == 0:
            return

        key = (datetime.now().date(), user_id)
        trigger_flush = False

        async with self._pending_lock:
            stat = self._pending_stats.get(key)
            if stat is None:
                stat = PendingStat()
                self._pending_stats[key] = stat
            stat.msg_number += msg_delta
            stat.repeat_time += repeat_delta
            self._pending_events += msg_delta + repeat_delta
            trigger_flush = self._pending_events >= max(plugin_config.repeat_flush_batch_size, 1)

        if trigger_flush:
            self._schedule_flush()

    def _schedule_flush(self) -> None:
        if self._flush_task and not self._flush_task.done():
            return

        task = asyncio.create_task(self._execute_flush())
        self._attach_flush_task(task)

    def _attach_flush_task(self, task: asyncio.Task[Any]) -> None:
        self._flush_task = task
        task.add_done_callback(lambda _: setattr(self, "_flush_task", None))

    async def _execute_flush(self) -> None:
        async with self._flush_lock:
            pending = await self._pop_pending()
            if not pending:
                return

            try:
                await self._write_pending(pending)
            except Exception:
                await self._restore_pending(pending)
                raise

    async def _pop_pending(self) -> dict[tuple[date, int], PendingStat]:
        async with self._pending_lock:
            pending = self._pending_stats
            self._pending_stats = {}
            self._pending_events = 0
            return pending

    async def _restore_pending(self, pending: dict[tuple[date, int], PendingStat]) -> None:
        async with self._pending_lock:
            for key, delta in pending.items():
                stat = self._pending_stats.get(key)
                if stat is None:
                    self._pending_stats[key] = PendingStat(delta.msg_number, delta.repeat_time)
                else:
                    stat.msg_number += delta.msg_number
                    stat.repeat_time += delta.repeat_time
                self._pending_events += delta.msg_number + delta.repeat_time

    async def _write_pending(self, pending: dict[tuple[date, int], PendingStat]) -> None:
        grouped: dict[date, dict[int, PendingStat]] = defaultdict(dict)
        for (record_date, uid), delta in pending.items():
            grouped[record_date][uid] = delta

        async with get_session() as session:
            for record_date, user_stats in grouped.items():
                stmt = (
                    select(MessageRecord)
                    .where(MessageRecord.session_id == self.session_id)
                    .where(MessageRecord.date == record_date)
                    .where(MessageRecord.uid.in_(list(user_stats.keys())))
                )
                records = await session.execute(stmt)
                existing = {record.uid: record for record in records.scalars()}

                for uid, delta in user_stats.items():
                    record = existing.get(uid)
                    if record:
                        record.msg_number += delta.msg_number
                        record.repeat_time += delta.repeat_time
                    else:
                        session.add(
                            MessageRecord(
                                date=record_date,
                                uid=uid,
                                msg_number=delta.msg_number,
                                repeat_time=delta.repeat_time,
                                session_id=self.session_id,
                            )
                        )

            await session.commit()
