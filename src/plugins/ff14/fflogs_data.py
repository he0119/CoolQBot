""" 一些数据

副本与职业数据
"""
import json
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx
from nonebot.log import logger

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


_boss_data: List = []
_job_data: List = []


async def load_data_from_repo():
    """ 从仓库获取数据 """
    logger.info('正在加载仓库数据')

    global _boss_data, _job_data
    async with httpx.AsyncClient() as client:
        r = await client.get(
            'https://cdn.jsdelivr.net/gh/he0119/coolqbot@master/src/plugins/ff14/fflogs_data.json',
            timeout=30)
        if r.status_code != 200:
            logger.error('仓库数据加载失败')
            return
        rjson = r.json()
        _boss_data = rjson['boss']
        _job_data = rjson['job']
        logger.info('仓库数据加载成功')
        # 同时保存一份文件在本地，以后就不用从网络获取
        with DATA.open('fflogs_data.json', open_mode='w',
                       encoding='utf8') as f:
            json.dump(rjson, f, ensure_ascii=False, indent=2)
            logger.info('已保存数据至本地')


async def load_data_from_local():
    """ 从本地获取数据 """
    logger.info('正在加载本地数据')

    global _boss_data, _job_data
    if DATA.exists('fflogs_data.json'):
        with DATA.open('fflogs_data.json', encoding='utf8') as f:
            data = json.load(f)
            _boss_data = data['boss']
            _job_data = data['job']
            logger.info('本地数据加载成功')
    else:
        logger.info('本地数据不存在')


async def load_data():
    """ 加载数据

    先从本地加载，如果失败则从仓库加载
    """
    if not _boss_data or not _job_data:
        await load_data_from_local()
    if not _boss_data or not _job_data:
        await load_data_from_repo()


async def update_data():
    """ 从网络更新数据 """
    await load_data_from_repo()


async def get_boss_data() -> List:
    """ 获取 boss 数据 """
    if not _boss_data:
        await load_data()
    return _boss_data


async def get_job_data() -> List:
    """ 获取 job 数据 """
    if not _job_data:
        await load_data()
    return _job_data


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


async def get_bosses_info() -> List[BossInfo]:
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


async def get_jobs_info() -> List[JobInfo]:
    """ 获取所有职业的相关信息 """
    job_info = []
    for job in await get_job_data():
        job_info.append(JobInfo(job['name'], job['spec']))
    return job_info
