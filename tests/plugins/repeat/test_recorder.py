"""Recorder 模块测试"""

from datetime import date, datetime, timedelta

import pytest
from nonebug import App
from pytest_mock import MockerFixture


class TestRecorderBasic:
    """Recorder 基础功能测试"""

    async def test_get_recorder_singleton(self, app: App):
        """测试 get_recorder 返回同一个实例（单例模式）"""
        from src.plugins.repeat.recorder import _RECORDER_REGISTRY, get_recorder

        recorder1 = get_recorder("test_session_1")
        recorder2 = get_recorder("test_session_1")
        recorder3 = get_recorder("test_session_2")

        assert recorder1 is recorder2
        assert recorder1 is not recorder3
        assert "test_session_1" in _RECORDER_REGISTRY
        assert "test_session_2" in _RECORDER_REGISTRY

    async def test_recorder_initial_state(self, app: App):
        """测试 Recorder 初始状态"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_initial_state")

        assert recorder.session_id == "test_initial_state"
        assert recorder._msg_send_time == []
        assert recorder._pending_stats == {}
        assert recorder._enabled is None


class TestRecorderMessageNumber:
    """消息数量统计测试"""

    async def test_message_number_empty(self, app: App):
        """测试空消息列表返回 0"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_msg_number_empty")
        count = recorder.message_number(5)

        assert count == 0

    async def test_message_number_within_time(self, app: App, mocker: MockerFixture):
        """测试统计指定时间内的消息数量"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_msg_number_within")
        now = datetime(2021, 1, 1, 12, 0, 0)

        mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
        mocked_datetime.now.return_value = now
        mocked_datetime.return_value = now

        # 添加一些消息时间
        recorder._msg_send_time = [
            now - timedelta(minutes=1),  # 1 分钟前
            now - timedelta(minutes=2),  # 2 分钟前
            now - timedelta(minutes=3),  # 3 分钟前
        ]

        # 统计 5 分钟内的消息
        count = recorder.message_number(5)
        assert count == 3

    async def test_message_number_partial_expired(self, app: App, mocker: MockerFixture):
        """测试部分消息过期的情况"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_msg_number_partial")
        now = datetime(2021, 1, 1, 12, 0, 0)

        mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
        mocked_datetime.now.return_value = now
        mocked_datetime.return_value = now

        recorder._msg_send_time = [
            now - timedelta(minutes=10),  # 10 分钟前（过期）
            now - timedelta(minutes=8),  # 8 分钟前（过期）
            now - timedelta(minutes=3),  # 3 分钟前
            now - timedelta(minutes=1),  # 1 分钟前
        ]

        # 统计 5 分钟内的消息
        count = recorder.message_number(5)
        assert count == 2

        # 过期消息应该被清除
        assert len(recorder._msg_send_time) == 2

    async def test_message_number_all_expired(self, app: App, mocker: MockerFixture):
        """测试所有消息都过期的情况"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_msg_number_all_expired")
        now = datetime(2021, 1, 1, 12, 0, 0)

        mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
        mocked_datetime.now.return_value = now
        mocked_datetime.return_value = now

        recorder._msg_send_time = [
            now - timedelta(minutes=10),
            now - timedelta(minutes=15),
        ]

        count = recorder.message_number(5)
        assert count == 0
        assert recorder._msg_send_time == []

    async def test_add_msg_send_time(self, app: App):
        """测试添加消息发送时间"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_add_msg_time")
        time1 = datetime(2021, 1, 1, 12, 0, 0)
        time2 = datetime(2021, 1, 1, 12, 1, 0)

        recorder.add_msg_send_time(time1)
        recorder.add_msg_send_time(time2)

        assert len(recorder._msg_send_time) == 2
        assert recorder._msg_send_time[0] == time1
        assert recorder._msg_send_time[1] == time2


class TestRecorderLastMessage:
    """最后消息时间测试"""

    async def test_last_message_on(self, app: App):
        """测试获取最后消息时间"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_last_msg")
        last_time = recorder.last_message_on()

        assert isinstance(last_time, datetime)

    async def test_reset_last_message_on(self, app: App, mocker: MockerFixture):
        """测试重置最后消息时间"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_reset_last_msg")
        expected_time = datetime(2021, 1, 1, 12, 0, 0)

        mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
        mocked_datetime.now.return_value = expected_time
        mocked_datetime.return_value = expected_time

        recorder.reset_last_message_on()

        assert recorder.last_message_on() == expected_time


class TestRecorderStats:
    """统计数据记录测试"""

    async def test_add_msg_number_list(self, app: App, mocker: MockerFixture):
        """测试添加消息数量记录"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_add_msg_number")
        today = date(2021, 1, 1)

        mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
        mocked_datetime.now.return_value = datetime(2021, 1, 1, 12, 0, 0)
        mocked_datetime.return_value = datetime(2021, 1, 1)

        await recorder.add_msg_number_list(user_id=123)

        assert (today, 123) in recorder._pending_stats
        stat = recorder._pending_stats[(today, 123)]
        assert stat.msg_number == 1
        assert stat.repeat_time == 0

    async def test_add_repeat_list(self, app: App, mocker: MockerFixture):
        """测试添加复读记录"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_add_repeat")
        today = date(2021, 1, 1)

        mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
        mocked_datetime.now.return_value = datetime(2021, 1, 1, 12, 0, 0)
        mocked_datetime.return_value = datetime(2021, 1, 1)

        await recorder.add_repeat_list(user_id=456)

        assert (today, 456) in recorder._pending_stats
        stat = recorder._pending_stats[(today, 456)]
        assert stat.msg_number == 1
        assert stat.repeat_time == 1

    async def test_add_multiple_stats(self, app: App, mocker: MockerFixture):
        """测试多次添加统计数据"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_multiple_stats")
        today = date(2021, 1, 1)

        mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
        mocked_datetime.now.return_value = datetime(2021, 1, 1, 12, 0, 0)
        mocked_datetime.return_value = datetime(2021, 1, 1)

        # 添加多次
        await recorder.add_msg_number_list(user_id=789)
        await recorder.add_msg_number_list(user_id=789)
        await recorder.add_repeat_list(user_id=789)

        stat = recorder._pending_stats[(today, 789)]
        assert stat.msg_number == 3
        assert stat.repeat_time == 1


class TestRecorderFlush:
    """缓存刷新测试"""

    async def test_flush_empty(self, app: App):
        """测试刷新空缓存"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_flush_empty")
        # 应该不会抛出异常
        await recorder.flush()

    async def test_flush_writes_to_db(self, app: App, mocker: MockerFixture):
        """测试刷新将数据写入数据库"""
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from src.plugins.repeat.models import MessageRecord
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_flush_write")
        today = date(2021, 1, 1)

        mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
        mocked_datetime.now.return_value = datetime(2021, 1, 1, 12, 0, 0)
        mocked_datetime.return_value = datetime(2021, 1, 1)

        # 添加统计数据
        await recorder.add_msg_number_list(user_id=100)
        await recorder.add_repeat_list(user_id=100)

        # 刷新到数据库
        await recorder.flush()

        # 验证数据库中的记录
        async with get_session() as session:
            stmt = select(MessageRecord).where(
                MessageRecord.session_id == "test_flush_write",
                MessageRecord.date == today,
                MessageRecord.uid == 100,
            )
            record = (await session.execute(stmt)).scalar_one_or_none()

        assert record is not None
        assert record.msg_number == 2
        assert record.repeat_time == 1

        # 缓存应该被清空
        assert recorder._pending_stats == {}

    async def test_flush_updates_existing_record(self, app: App, mocker: MockerFixture):
        """测试刷新更新已存在的数据库记录"""
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from src.plugins.repeat.models import MessageRecord
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_flush_update")
        today = date(2021, 1, 1)

        mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
        mocked_datetime.now.return_value = datetime(2021, 1, 1, 12, 0, 0)
        mocked_datetime.return_value = datetime(2021, 1, 1)

        # 先创建一条记录
        async with get_session() as session:
            session.add(
                MessageRecord(
                    date=today,
                    uid=200,
                    msg_number=5,
                    repeat_time=2,
                    session_id="test_flush_update",
                )
            )
            await session.commit()

        # 添加新的统计数据
        await recorder.add_msg_number_list(user_id=200)
        await recorder.add_repeat_list(user_id=200)

        # 刷新到数据库
        await recorder.flush()

        # 验证数据库中的记录被更新
        async with get_session() as session:
            stmt = select(MessageRecord).where(
                MessageRecord.session_id == "test_flush_update",
                MessageRecord.date == today,
                MessageRecord.uid == 200,
            )
            record = (await session.execute(stmt)).scalar_one_or_none()

        assert record is not None
        assert record.msg_number == 7  # 5 + 2
        assert record.repeat_time == 3  # 2 + 1


class TestRecorderGetRecords:
    """获取记录测试"""

    async def test_get_records_current_month(self, app: App, mocker: MockerFixture):
        """测试获取当月记录"""
        from nonebot_plugin_orm import get_session

        from src.plugins.repeat.models import MessageRecord
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_get_records_month")

        mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
        mocked_datetime.now.return_value = datetime(2021, 1, 15, 12, 0, 0)
        mocked_datetime.return_value = datetime(2021, 1, 15)

        # 创建测试数据
        async with get_session() as session:
            session.add(
                MessageRecord(
                    date=date(2021, 1, 10),
                    uid=100,
                    msg_number=10,
                    repeat_time=5,
                    session_id="test_get_records_month",
                )
            )
            session.add(
                MessageRecord(
                    date=date(2021, 1, 12),
                    uid=100,
                    msg_number=8,
                    repeat_time=3,
                    session_id="test_get_records_month",
                )
            )
            # 上个月的记录（不应该被返回）
            session.add(
                MessageRecord(
                    date=date(2020, 12, 25),
                    uid=100,
                    msg_number=20,
                    repeat_time=10,
                    session_id="test_get_records_month",
                )
            )
            await session.commit()

        # 获取当月记录
        records = await recorder.get_records()

        assert len(records) == 2

    async def test_get_records_specific_month(self, app: App):
        """测试获取指定月份的记录"""
        from nonebot_plugin_orm import get_session

        from src.plugins.repeat.models import MessageRecord
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_get_records_specific")

        # 创建测试数据
        async with get_session() as session:
            session.add(
                MessageRecord(
                    date=date(2021, 6, 15),
                    uid=100,
                    msg_number=10,
                    repeat_time=5,
                    session_id="test_get_records_specific",
                )
            )
            session.add(
                MessageRecord(
                    date=date(2021, 7, 1),
                    uid=100,
                    msg_number=8,
                    repeat_time=3,
                    session_id="test_get_records_specific",
                )
            )
            await session.commit()

        # 获取 2021 年 6 月的记录
        records = await recorder.get_records(year=2021, month=6)

        assert len(records) == 1
        assert records[0].date == date(2021, 6, 15)

    async def test_get_records_december(self, app: App):
        """测试获取 12 月的记录（边界情况）"""
        from nonebot_plugin_orm import get_session

        from src.plugins.repeat.models import MessageRecord
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_get_records_december")

        # 创建测试数据
        async with get_session() as session:
            session.add(
                MessageRecord(
                    date=date(2021, 12, 25),
                    uid=100,
                    msg_number=10,
                    repeat_time=5,
                    session_id="test_get_records_december",
                )
            )
            session.add(
                MessageRecord(
                    date=date(2022, 1, 1),
                    uid=100,
                    msg_number=8,
                    repeat_time=3,
                    session_id="test_get_records_december",
                )
            )
            await session.commit()

        # 获取 2021 年 12 月的记录
        records = await recorder.get_records(year=2021, month=12)

        assert len(records) == 1
        assert records[0].date == date(2021, 12, 25)

    async def test_get_records_year_none_raises(self, app: App):
        """测试 year 为 None 但 month 不为 None 时抛出异常"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_get_records_year_none")

        with pytest.raises(ValueError, match="year 不能为 None"):
            await recorder.get_records(year=None, month=6)

    async def test_get_records_month_none_raises(self, app: App):
        """测试 month 为 None 但 year 不为 None 时抛出异常"""
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_get_records_month_none")

        with pytest.raises(ValueError, match="month 不能为 None"):
            await recorder.get_records(year=2021, month=None)

    async def test_get_records_by_day(self, app: App):
        """测试获取指定日期的记录"""
        from nonebot_plugin_orm import get_session

        from src.plugins.repeat.models import MessageRecord
        from src.plugins.repeat.recorder import get_recorder

        recorder = get_recorder("test_get_records_day")

        # 创建测试数据
        async with get_session() as session:
            session.add(
                MessageRecord(
                    date=date(2021, 6, 15),
                    uid=100,
                    msg_number=10,
                    repeat_time=5,
                    session_id="test_get_records_day",
                )
            )
            session.add(
                MessageRecord(
                    date=date(2021, 6, 15),
                    uid=200,
                    msg_number=8,
                    repeat_time=3,
                    session_id="test_get_records_day",
                )
            )
            session.add(
                MessageRecord(
                    date=date(2021, 6, 16),
                    uid=100,
                    msg_number=5,
                    repeat_time=2,
                    session_id="test_get_records_day",
                )
            )
            await session.commit()

        # 获取 2021 年 6 月 15 日的记录
        records = await recorder.get_records_by_day(year=2021, month=6, day=15)

        assert len(records) == 2


class TestFlushAllRecorders:
    """全局刷新测试"""

    async def test_flush_all_recorders_empty(self, app: App):
        """测试刷新空的 recorder 注册表"""
        from src.plugins.repeat.recorder import _RECORDER_REGISTRY, flush_all_recorders

        _RECORDER_REGISTRY.clear()
        # 应该不会抛出异常
        await flush_all_recorders()

    async def test_flush_all_recorders_multiple(self, app: App, mocker: MockerFixture):
        """测试同时刷新多个 recorder"""
        from nonebot_plugin_orm import get_session
        from sqlalchemy import select

        from src.plugins.repeat.models import MessageRecord
        from src.plugins.repeat.recorder import flush_all_recorders, get_recorder

        today = date(2021, 1, 1)

        mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
        mocked_datetime.now.return_value = datetime(2021, 1, 1, 12, 0, 0)
        mocked_datetime.return_value = datetime(2021, 1, 1)

        # 创建多个 recorder 并添加数据
        recorder1 = get_recorder("test_flush_all_1")
        recorder2 = get_recorder("test_flush_all_2")

        await recorder1.add_msg_number_list(user_id=100)
        await recorder2.add_repeat_list(user_id=200)

        # 全局刷新
        await flush_all_recorders()

        # 验证两个 recorder 的数据都被写入
        async with get_session() as session:
            stmt1 = select(MessageRecord).where(
                MessageRecord.session_id == "test_flush_all_1",
                MessageRecord.date == today,
            )
            record1 = (await session.execute(stmt1)).scalar_one_or_none()

            stmt2 = select(MessageRecord).where(
                MessageRecord.session_id == "test_flush_all_2",
                MessageRecord.date == today,
            )
            record2 = (await session.execute(stmt2)).scalar_one_or_none()

        assert record1 is not None
        assert record1.msg_number == 1
        assert record1.repeat_time == 0

        assert record2 is not None
        assert record2.msg_number == 1
        assert record2.repeat_time == 1

        # 缓存应该被清空
        assert recorder1._pending_stats == {}
        assert recorder2._pending_stats == {}


class TestPendingStat:
    """PendingStat 数据类测试"""

    async def test_pending_stat_default(self, app: App):
        """测试 PendingStat 默认值"""
        from src.plugins.repeat.recorder import PendingStat

        stat = PendingStat()
        assert stat.msg_number == 0
        assert stat.repeat_time == 0

    async def test_pending_stat_with_values(self, app: App):
        """测试 PendingStat 带初始值"""
        from src.plugins.repeat.recorder import PendingStat

        stat = PendingStat(msg_number=10, repeat_time=5)
        assert stat.msg_number == 10
        assert stat.repeat_time == 5
