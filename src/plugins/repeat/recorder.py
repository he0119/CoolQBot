""" 数据记录

记录排行版，历史，状态所需的数据
如果遇到老版本数据，则自动升级
"""
from datetime import datetime, timedelta

from nonebot.log import logger
from nonebot_plugin_datastore import create_session, get_plugin_data
from nonebot_plugin_datastore.db import post_db_init
from sqlalchemy import select

from . import plugin_config
from .models import Record

plugin_data = get_plugin_data()

VERSION = "1"


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


class Recorder:
    def __init__(self):
        # 启动时间
        self.start_time = datetime.now()

        self._msg_send_time: dict[tuple, list[datetime]] = {}
        self._last_message_on: dict[tuple, datetime] = {}

    def message_number(
        self,
        x: int,
        platform: str,
        group_id: str | None,
        guild_id: str | None,
        channel_id: str | None,
    ):
        """返回指定群 x 分钟内的消息条数，并清除之前的消息记录"""
        key = (platform, group_id, guild_id, channel_id)

        times = self._msg_send_time.get(key, [])
        now = datetime.now()
        for i in range(len(times)):
            if times[i] > now - timedelta(minutes=x):
                self._msg_send_time[key] = times[i:]
                return len(self._msg_send_time[key])

        # 如果没有满足条件的消息，则清除记录
        self._msg_send_time[key] = []
        return 0

        #     def repeat_list(self, group_id: int):
        #         """获取指定群整个月的复读记录"""
        #         return self._merge_list(self._repeat_list[group_id])

        #     def msg_number_list(self, group_id: int):
        #         """获取指定群整个月的消息数量记录"""
        #         return self._merge_list(self._msg_number_list[group_id])

        #     def repeat_list_by_day(self, day, group_id: int):
        #         """获取指定群某一天的复读记录"""
        #         if day in self._repeat_list[group_id]:
        #             return self._repeat_list[group_id][day]
        #         return {}

        #     def msg_number_list_by_day(self, day, group_id: int):
        #         """获取指定群某一天的消息数量记录"""
        #         if day in self._msg_number_list[group_id]:
        #             return self._msg_number_list[group_id][day]
        #         return {}

    async def add_repeat_list(
        self,
        platform: str,
        user_id: str,
        group_id: str | None,
        guild_id: str | None,
        channel_id: str | None,
    ):
        """该 QQ 号在指定群的复读记录，加一"""
        now_date = datetime.now().date()
        async with create_session() as session:
            record = await session.scalar(
                select(Record)
                .where(Record.date == now_date)
                .where(Record.platform == platform)
                .where(Record.user_id == user_id)
                .where(Record.group_id == group_id)
                .where(Record.guild_id == guild_id)
                .where(Record.channel_id == channel_id)
            )
            if record:
                record.msg_number += 1
                record.repeat_time += 1
                await session.commit()
            else:
                record = Record(
                    date=now_date,
                    platform=platform,
                    user_id=user_id,
                    group_id=group_id,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    msg_number=1,
                    repeat_time=1,
                )
                session.add(record)
                await session.commit()

    async def add_msg_number_list(
        self,
        platform: str,
        user_id: str,
        group_id: str | None,
        guild_id: str | None,
        channel_id: str | None,
    ):
        """该 QQ 号在指定群的消息数量记录，加一"""
        now_date = datetime.now().date()
        async with create_session() as session:
            record = await session.scalar(
                select(Record)
                .where(Record.date == now_date)
                .where(Record.platform == platform)
                .where(Record.user_id == user_id)
                .where(Record.group_id == group_id)
                .where(Record.guild_id == guild_id)
                .where(Record.channel_id == channel_id)
            )
            if record:
                record.msg_number += 1
                await session.commit()
            else:
                record = Record(
                    date=now_date,
                    platform=platform,
                    user_id=user_id,
                    group_id=group_id,
                    guild_id=guild_id,
                    channel_id=channel_id,
                    msg_number=1,
                )
                session.add(record)
                await session.commit()

    def add_msg_send_time(
        self,
        time,
        platform: str,
        group_id: str | None,
        guild_id: str | None,
        channel_id: str | None,
    ):
        """将这个时间加入到指定群的消息发送时间列表中"""
        key = (platform, group_id, guild_id, channel_id)
        if key not in self._msg_send_time:
            self._msg_send_time[key] = []
        self._msg_send_time[key].append(time)

    def last_message_on(
        self,
        platform: str,
        group_id: str | None,
        guild_id: str | None,
        channel_id: str | None,
    ):
        return self._last_message_on.get(
            (platform, group_id, guild_id, channel_id), None
        )

    def reset_last_message_on(
        self,
        platform: str,
        group_id: str | None,
        guild_id: str | None,
        channel_id: str | None,
    ):
        self._last_message_on[
            (platform, group_id, guild_id, channel_id)
        ] = datetime.now()


#     def _add_to_list(self, recrod_list, qq, group_id: int):
#         """添加数据进列表"""
#         day = datetime.now().day
#         if day not in recrod_list[group_id]:
#             recrod_list[group_id][day] = {}
#         try:
#             recrod_list[group_id][day][qq] += 1
#         except KeyError:
#             recrod_list[group_id][day][qq] = 1

#     def _merge_list(self, recrod_list):
#         """合并词典中按天数存储的数据"""
#         new_list = {}
#         for day_list in recrod_list:
#             for qq in recrod_list[day_list]:
#                 if qq in new_list:
#                     new_list[qq] += recrod_list[day_list][qq]
#                 else:
#                     new_list[qq] = recrod_list[day_list][qq]
#         return new_list

#     def _load_data(self):
#         """加载数据"""
#         if not DATA.exists(self._name):
#             logger.warning(f"{self._name} 复读记录文件不存在！")
#             return

#         data = DATA.load_pkl(self._name)

#         # 如果是老版本格式的数据则先升级在加载
#         # 默认使用配置中第一个群来升级老数据
#         if "version" not in data or data["version"] != VERSION:
#             logger.info("发现旧版本数据，正在升级数据")
#             data = update(data, plugin_config.group_id[0])
#             DATA.dump_pkl(data, self._name)
#             logger.info("升级数据成功")

#         # 加载数据
#         self._last_message_on = data["last_message_on"]
#         self._msg_send_time = data["msg_send_time"]
#         self._repeat_list = data["repeat_list"]
#         self._msg_number_list = data["msg_number_list"]

#         self.add_new_group()

#     def add_new_group(self):
#         """如果群列表新加了群，则补充所需的数据"""
#         for group_id in plugin_config.group_id:
#             if group_id not in self._last_message_on:
#                 self._last_message_on[group_id] = datetime.now()

#             if group_id not in self._msg_send_time:
#                 self._msg_send_time[group_id] = []

#             if group_id not in self._repeat_list:
#                 self._repeat_list[group_id] = {}

#             if group_id not in self._msg_number_list:
#                 self._msg_number_list[group_id] = {}

#     def save_data(self):
#         """保存数据"""
#         DATA.dump_pkl(self.get_data(), self._name)

#     def save_data_to_history(self):
#         """保存数据到历史文件夹"""
#         date = datetime.now() - timedelta(hours=1)
#         DATA.dump_pkl(self.get_data(), self.get_history_pkl_name(date))

#     def get_data(self):
#         """获取当前数据

#         并附带上数据的版本
#         """
#         return {
#             "version": VERSION,
#             "last_message_on": self._last_message_on,
#             "msg_send_time": self._msg_send_time,
#             "repeat_list": self._repeat_list,
#             "msg_number_list": self._msg_number_list,
#         }

#     def init_data(self):
#         """初始化数据"""
#         self._last_message_on = {
#             group_id: datetime.now() for group_id in plugin_config.group_id
#         }
#         self._msg_send_time = {group_id: [] for group_id in plugin_config.group_id}
#         self._repeat_list = {group_id: {} for group_id in plugin_config.group_id}
#         self._msg_number_list = {group_id: {} for group_id in plugin_config.group_id}

#     @staticmethod
#     def get_history_pkl_name(dt: datetime):
#         time_str = dt.strftime("%Y-%m")
#         return f"{time_str}.pkl"


@post_db_init
async def data_migration():
    """迁移数据"""
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
    async with create_session() as session:
        for file in plugin_data.data_dir.glob("*.pkl"):
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
            for (date, group_id, user_id), values in users.items():
                record = Record(
                    date=datetime.strptime(date, "%Y-%m-%d").date(),
                    platform="qq",
                    group_id=group_id,
                    user_id=user_id,
                    **values,
                )
                session.add(record)
        await session.commit()
    logger.info("迁移数据成功")
