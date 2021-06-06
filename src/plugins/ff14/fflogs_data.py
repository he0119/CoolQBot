""" 一些数据

副本与职业数据
"""
from dataclasses import dataclass
from typing import Optional

from .config import DATA


@dataclass
class BossInfo:
    """ BOSS 的信息 """
    name: str
    zone: int
    encounter: int
    difficulty: int


@dataclass
class JobInfo:
    """ 职业的信息 """
    name: str
    spec: int


FFLOGS_DATA = DATA.network_file(
    'https://cdn.jsdelivr.net/gh/he0119/coolqbot@master/src/plugins/ff14/fflogs_data.json',
    'fflogs_data.json',
)


async def get_boss_data() -> list:
    """ 获取 boss 数据 """
    data = await FFLOGS_DATA.data
    return data['boss']


async def get_job_data() -> list:
    """ 获取 job 数据 """
    data = await FFLOGS_DATA.data
    return data['job']


async def get_boss_info_by_nickname(name: str) -> Optional[BossInfo]:
    """ 根据昵称获取 BOSS 的相关信息

    :param name: BOSS 的昵称
    :returns: 返回包含 `name`, `zone`, `encounter`, `difficulty` 信息的数据类，如果找不到返回 None
    """
    for boss in await get_boss_data():
        if name.lower() in [boss['name'], *boss['nicknames']]:
            return BossInfo(
                boss['name'],
                boss['zone'],
                boss['encounter'],
                boss['difficulty'],
            )
    return None


async def get_bosses_info() -> list[BossInfo]:
    """ 获取所有 BOSS 的相关信息 """
    boss_info = []
    for boss in await get_boss_data():
        boss_info.append(
            BossInfo(
                boss['name'],
                boss['zone'],
                boss['encounter'],
                boss['difficulty'],
            ))
    return boss_info


async def get_job_info_by_nickname(name: str) -> Optional[JobInfo]:
    """ 根据昵称获取职业的相关信息

    :param name: 职业的昵称
    :returns: 返回包含 `name`, `spec` 信息的数据类，如果找不到返回 None
    """
    for job in await get_job_data():
        if name in [job['name'], *job['nicknames']]:
            return JobInfo(job['name'], job['spec'])
    return None


async def get_jobs_info() -> list[JobInfo]:
    """ 获取所有职业的相关信息 """
    job_info = []
    for job in await get_job_data():
        job_info.append(JobInfo(job['name'], job['spec']))
    return job_info
