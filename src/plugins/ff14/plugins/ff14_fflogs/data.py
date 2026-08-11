"""一些数据

副本与职业数据
"""

from nonebot_plugin_localstore import get_plugin_cache_dir

from src.utils.remote_data import RemoteJsonData

from .models import BossInfo, FFlogsDataModel, JobInfo


def parse_data(data: dict) -> FFlogsDataModel:
    """解析数据"""
    return FFlogsDataModel.model_validate(data)


FFLOGS_DATA = RemoteJsonData(
    "https://bot-docs.hehome.xyz/fflogs_data.json",
    lambda: get_plugin_cache_dir() / "fflogs_data.json",
    parse_data,
)


async def get_boss_info_by_nickname(name: str) -> BossInfo | None:
    """根据昵称获取 BOSS 的相关信息

    :param name: BOSS 的昵称
    :returns: 返回包含 `name`, `zone`, `encounter`, `difficulty` 信息的数据类，如果找不到返回 None
    """
    data = await FFLOGS_DATA.data
    for boss in data.boss:
        if name.lower() in [boss.name, *boss.nicknames]:
            return boss
    return None


async def get_job_info_by_nickname(name: str) -> JobInfo | None:
    """根据昵称获取职业的相关信息

    :param name: 职业的昵称
    :returns: 返回包含 `name`, `spec` 信息的数据类，如果找不到返回 None
    """
    data = await FFLOGS_DATA.data
    for job in data.job:
        if name.lower() in [job.name, *job.nicknames]:
            return job
    return None
