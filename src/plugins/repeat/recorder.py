"""数据记录

记录排行版，历史，状态所需的数据
如果遇到老版本数据，则自动升级
"""

import asyncio
import bisect
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from src.utils.annotated import AsyncSession

from .config import plugin_config
from .models import Enabled, MessageRecord


@dataclass(slots=True)
class PendingStat:
    msg_number: int = 0
    repeat_time: int = 0


_RECORDER_REGISTRY: dict[str, "Recorder"] = {}
_GLOBAL_FLUSH_LOCK = asyncio.Lock()


async def _collect_all_pending() -> dict[tuple[str, date, int], PendingStat]:
    """从所有 Recorder 收集待写入数据"""
    collected: dict[tuple[str, date, int], PendingStat] = {}

    for recorder in _RECORDER_REGISTRY.values():
        async with recorder._pending_lock:
            for (record_date, uid), stat in recorder._pending_stats.items():
                key = (recorder.session_id, record_date, uid)
                if key in collected:
                    collected[key].msg_number += stat.msg_number
                    collected[key].repeat_time += stat.repeat_time
                else:
                    collected[key] = PendingStat(stat.msg_number, stat.repeat_time)
            recorder._pending_stats.clear()

    return collected


async def _restore_pending(pending: dict[tuple[str, date, int], PendingStat]) -> None:
    """写入失败时恢复数据到对应的 Recorder"""
    # 按 session_id 分组
    by_session: dict[str, dict[tuple[date, int], PendingStat]] = defaultdict(dict)
    for (session_id, record_date, uid), stat in pending.items():
        by_session[session_id][(record_date, uid)] = stat

    for session_id, stats in by_session.items():
        if session_id in _RECORDER_REGISTRY:
            recorder = _RECORDER_REGISTRY[session_id]
            async with recorder._pending_lock:
                for key, delta in stats.items():
                    existing = recorder._pending_stats.get(key)
                    if existing:
                        existing.msg_number += delta.msg_number
                        existing.repeat_time += delta.repeat_time
                    else:
                        recorder._pending_stats[key] = PendingStat(delta.msg_number, delta.repeat_time)


async def _batch_write_to_db(
    pending: dict[tuple[str, date, int], PendingStat],
) -> None:
    """批量写入数据库（单次事务）"""
    if not pending:
        return

    # 按 (session_id, date) 分组以优化查询
    grouped: dict[tuple[str, date], dict[int, PendingStat]] = defaultdict(dict)
    for (session_id, record_date, uid), stat in pending.items():
        grouped[(session_id, record_date)][uid] = stat

    async with get_session() as session:
        for (session_id, record_date), user_stats in grouped.items():
            stmt = (
                select(MessageRecord)
                .where(MessageRecord.session_id == session_id)
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
                            session_id=session_id,
                        )
                    )

        await session.commit()


async def flush_all_recorders() -> None:
    """批量收集并写入所有 Recorder 的缓存数据（单次数据库事务）"""
    if not _RECORDER_REGISTRY:
        return

    pending: dict[tuple[str, date, int], PendingStat] = {}
    async with _GLOBAL_FLUSH_LOCK:
        try:
            pending = await _collect_all_pending()
            await _batch_write_to_db(pending)
        except Exception as e:
            logger.opt(exception=e).warning("Failed to flush repeat statistics")
            # 恢复数据
            if pending:
                await _restore_pending(pending)


if plugin_config.repeat_flush_interval > 0:
    # 使用 apscheduler 设置定时刷新任务
    scheduler.add_job(
        flush_all_recorders,
        "interval",
        seconds=max(plugin_config.repeat_flush_interval, 1),
        id="repeat_flush",
    )


def get_recorder(session_id: str) -> "Recorder":
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
        """返回指定群 x 分钟内的消息条数，并清除之前的消息记录

        使用二分查找优化性能
        """
        if not self._msg_send_time:
            return 0

        threshold = datetime.now() - timedelta(minutes=x)
        # 使用二分查找找到第一个大于阈值的位置
        idx = bisect.bisect_right(self._msg_send_time, threshold)

        if idx >= len(self._msg_send_time):
            # 所有消息都过期了
            self._msg_send_time.clear()
            return 0

        # 只保留未过期的消息
        if idx > 0:
            del self._msg_send_time[:idx]

        return len(self._msg_send_time)

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
        await self.flush()

        time = date(year, month, day)
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
        """刷新当前 Recorder 的缓存数据"""
        # 先获取待写入数据（快速操作，减少锁持有时间）
        async with self._pending_lock:
            if not self._pending_stats:
                return
            pending = self._pending_stats
            self._pending_stats = {}

        # 转换为全局格式
        global_pending: dict[tuple[str, date, int], PendingStat] = {}
        for (record_date, uid), stat in pending.items():
            global_pending[(self.session_id, record_date, uid)] = stat

        # 写入数据库（使用全局锁避免并发写入冲突）
        async with _GLOBAL_FLUSH_LOCK:
            try:
                await _batch_write_to_db(global_pending)
            except Exception:
                # 失败时恢复数据
                async with self._pending_lock:
                    for (_, record_date, uid), delta in global_pending.items():
                        key = (record_date, uid)
                        stat = self._pending_stats.get(key)
                        if stat is None:
                            self._pending_stats[key] = PendingStat(delta.msg_number, delta.repeat_time)
                        else:
                            stat.msg_number += delta.msg_number
                            stat.repeat_time += delta.repeat_time
                raise

    async def _record_stat(self, user_id: int, msg_delta: int, repeat_delta: int) -> None:
        if msg_delta == 0 and repeat_delta == 0:
            return

        key = (datetime.now().date(), user_id)

        async with self._pending_lock:
            stat = self._pending_stats.get(key)
            if stat is None:
                stat = PendingStat()
                self._pending_stats[key] = stat
            stat.msg_number += msg_delta
            stat.repeat_time += repeat_delta
