""" 数据记录

记录排行版，历史，状态所需的数据
如果遇到老版本数据，则自动升级
"""
from datetime import date, datetime, timedelta

from nonebot import get_driver
from nonebot.log import logger
from nonebot_plugin_datastore import get_plugin_data
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from src.utils.annotated import GroupInfo

from . import plugin_config
from .models import Enabled, MessageRecord

VERSION = "1"

plugin_data = get_plugin_data()


def update(data: dict) -> dict:
    """升级脚本

    升级 0.8.1 及以前版本的 recorder 数据。
    """
    if "version" not in data or data["version"] != VERSION:
        logger.info("发现旧版本数据，正在升级数据")
        if not plugin_config.repeat_migration_group_id:
            raise RuntimeError("未配置群，无法升级数据")
        # 判断是那种类型的数据
        if isinstance(list(data.values())[0], int):
            return update_old_1(data, plugin_config.repeat_migration_group_id)
        else:
            return update_old_2(data, plugin_config.repeat_migration_group_id)
    return data


def update_old_1(data: dict, group_id: int):
    """升级 0.7.0 之前版本的数据"""
    new_data = {}
    # 添加版本信息
    new_data["version"] = VERSION

    # 升级 last_message_on
    new_data["last_message_on"] = {}
    new_data["last_message_on"][group_id] = data["last_message_on"]

    # 升级 msg_send_time
    new_data["msg_send_time"] = {}
    new_data["msg_send_time"][group_id] = []

    # 升级 repeat_list
    new_data["repeat_list"] = {}
    new_data["repeat_list"][group_id] = data["repeat_list"]

    # 升级 msg_number_list
    new_data["msg_number_list"] = {}
    new_data["msg_number_list"][group_id] = data["msg_number_list"]
    return new_data


def update_old_2(data: dict, group_id: int):
    """升级 0.7.0-0.8.1 版本的 recorder 数据"""
    new_data = {}
    # 添加版本信息
    new_data["version"] = VERSION

    # 升级 last_message_on
    new_data["last_message_on"] = {}
    new_data["last_message_on"][group_id] = data["last_message_on"]

    # 升级 msg_send_time
    new_data["msg_send_time"] = {}
    new_data["msg_send_time"][group_id] = []

    # 升级 repeat_list
    new_data["repeat_list"] = {}
    new_data["repeat_list"][group_id] = data["repeat_list"]

    # 升级 msg_number_list
    new_data["msg_number_list"] = {}
    new_data["msg_number_list"][group_id] = data["msg_number_list"]
    return new_data


class Singleton(type):
    _instances = {}

    def __call__(cls, group_info: GroupInfo):
        if group_info not in cls._instances:
            cls._instances[group_info] = super().__call__(group_info)
        return cls._instances[group_info]


class Recorder(metaclass=Singleton):
    def __init__(self, group_info: GroupInfo):
        self._msg_send_time: list[datetime] = []
        self._last_message_on: datetime = datetime.now()

        self.group_info = group_info

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
                .where(MessageRecord.platform == self.group_info.platform)
                .where(MessageRecord.group_id == self.group_info.group_id)
                .where(MessageRecord.guild_id == self.group_info.guild_id)
                .where(MessageRecord.channel_id == self.group_info.channel_id)
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
                .where(MessageRecord.platform == self.group_info.platform)
                .where(MessageRecord.group_id == self.group_info.group_id)
                .where(MessageRecord.guild_id == self.group_info.guild_id)
                .where(MessageRecord.channel_id == self.group_info.channel_id)
                .where(MessageRecord.date == time)
            )
            return records.scalars().all()

    async def add_repeat_list(self, user_id: str):
        """该 QQ 号在指定群的复读记录，加一"""
        now_date = datetime.now().date()
        async with get_session() as session:
            record = await session.scalar(
                select(MessageRecord)
                .where(MessageRecord.date == now_date)
                .where(MessageRecord.user_id == user_id)
                .where(MessageRecord.platform == self.group_info.platform)
                .where(MessageRecord.group_id == self.group_info.group_id)
                .where(MessageRecord.guild_id == self.group_info.guild_id)
                .where(MessageRecord.channel_id == self.group_info.channel_id)
            )
            if record:
                record.msg_number += 1
                record.repeat_time += 1
                await session.commit()
            else:
                record = MessageRecord(
                    date=now_date,
                    user_id=user_id,
                    msg_number=1,
                    repeat_time=1,
                    **self.group_info.dict(),
                )
                session.add(record)
                await session.commit()

    async def add_msg_number_list(self, user_id: str):
        """该 QQ 号在指定群的消息数量记录，加一"""
        now_date = datetime.now().date()
        async with get_session() as session:
            record = await session.scalar(
                select(MessageRecord)
                .where(MessageRecord.date == now_date)
                .where(MessageRecord.user_id == user_id)
                .where(MessageRecord.platform == self.group_info.platform)
                .where(MessageRecord.group_id == self.group_info.group_id)
                .where(MessageRecord.guild_id == self.group_info.guild_id)
                .where(MessageRecord.channel_id == self.group_info.channel_id)
            )
            if record:
                record.msg_number += 1
                await session.commit()
            else:
                record = MessageRecord(
                    date=now_date,
                    user_id=user_id,
                    msg_number=1,
                    **self.group_info.dict(),
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
            return (
                await session.scalars(
                    select(Enabled)
                    .where(Enabled.platform == self.group_info.platform)
                    .where(Enabled.group_id == self.group_info.group_id)
                    .where(Enabled.guild_id == self.group_info.guild_id)
                    .where(Enabled.channel_id == self.group_info.channel_id)
                )
            ).one_or_none()


@get_driver().on_startup
async def data_migration():
    """迁移数据"""
    files = list(plugin_data.data_dir.glob("*.pkl"))
    if not files:
        return

    if not plugin_config.repeat_migration_group_id:
        logger.warning("未配置默认群，无法迁移数据")
        return

    logger.info("正在迁移数据")
    # {
    #    "last_message_on": { group_id: datetime },
    #    "msg_send_time": { group_id: [datetime] },
    #    "repeat_list": { group_id: { day: { user_id: int } } },
    #    "msg_number_list": { group_id: { day: { user_id: int } } },
    # }
    async with get_session() as session:
        for file in files:
            if file.stem == "recorder":
                record_date = datetime.now().date()
            else:
                record_date = datetime.strptime(file.stem, "%Y-%m").date()

            data = plugin_data.load_pkl(file.name)
            data = update(data)
            users = {}
            for group_id, days in data["repeat_list"].items():
                for day in days:
                    # TODO: 有些数据的日期是 0，暂时跳过
                    if day == 0:
                        continue
                    record_date = record_date.replace(day=day)
                    date_str = record_date.strftime("%Y-%m-%d")
                    for user_id, repeat_time in days[day].items():
                        users[(date_str, group_id, user_id)] = {
                            "repeat_time": repeat_time
                        }
            for group_id, days in data["msg_number_list"].items():
                for day in days:
                    if day == 0:
                        continue
                    record_date = record_date.replace(day=day)
                    date_str = record_date.strftime("%Y-%m-%d")
                    for user_id, msg_number in days[day].items():
                        if (date_str, group_id, user_id) in users:
                            users[(date_str, group_id, user_id)][
                                "msg_number"
                            ] = msg_number
                        else:
                            users[(date_str, group_id, user_id)] = {
                                "msg_number": msg_number
                            }
            for (date_str, group_id, user_id), values in users.items():
                record = MessageRecord(
                    date=datetime.strptime(date_str, "%Y-%m-%d").date(),
                    platform="qq",
                    group_id=group_id,
                    user_id=user_id,
                    **values,
                )
                session.add(record)
            await session.commit()
            file.rename(file.with_suffix(".pkl.bak"))
    logger.info("迁移数据成功")
