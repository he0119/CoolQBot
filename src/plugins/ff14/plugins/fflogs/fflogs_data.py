""" 一些数据

副本与职业数据
"""
from typing import Optional

from pydantic import BaseModel

from ... import DATA


class BossInfo(BaseModel):
    """BOSS 的信息"""

    name: str
    nicknames: list[str]
    zone: int
    encounter: int
    difficulty: int


class JobInfo(BaseModel):
    """职业的信息"""

    name: str
    nicknames: list[str]
    spec: int


class FFlogsDataModel(BaseModel):
    version: str
    boss: list[BossInfo]
    job: list[JobInfo]


def parse_data(data: dict) -> FFlogsDataModel:
    """解析数据"""
    return FFlogsDataModel.parse_obj(data)


FFLOGS_DATA = DATA.network_file(
    "https://raw.fastgit.org/he0119/CoolQBot/master/src/plugins/ff14/fflogs_data.json",
    "fflogs_data.json",
    parse_data,  # type: ignore
)


async def get_boss_info_by_nickname(name: str) -> Optional[BossInfo]:
    """根据昵称获取 BOSS 的相关信息

    :param name: BOSS 的昵称
    :returns: 返回包含 `name`, `zone`, `encounter`, `difficulty` 信息的数据类，如果找不到返回 None
    """
    data = await FFLOGS_DATA.data
    for boss in data.boss:
        if name.lower() in [boss.name, *boss.nicknames]:
            return boss
    return None


async def get_job_info_by_nickname(name: str) -> Optional[JobInfo]:
    """根据昵称获取职业的相关信息

    :param name: 职业的昵称
    :returns: 返回包含 `name`, `spec` 信息的数据类，如果找不到返回 None
    """
    data = await FFLOGS_DATA.data
    for job in data.job:
        if name.lower() in [job.name, *job.nicknames]:
            return job
    return None
