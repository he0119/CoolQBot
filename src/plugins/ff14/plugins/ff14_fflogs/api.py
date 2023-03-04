""" FFLogs API

v1 版的 API，现在已经废弃，没有维护
以后可能会失效
文档网址 https://cn.fflogs.com/v1/docs
"""
import asyncio
import json
import math
from datetime import datetime, timedelta
from random import randint
from typing import Literal, cast

import httpx
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_datastore import create_session, get_plugin_data
from nonebot_plugin_datastore.db import post_db_init
from pydantic import ValidationError, parse_obj_as
from sqlalchemy import select

from .config import plugin_config
from .data import (
    FFLOGS_DATA,
    FFlogsDataModel,
    get_boss_info_by_nickname,
    get_job_info_by_nickname,
)
from .models import CharacterRanking, Class, FFLogsRanking, Ranking, User, Zones

plugin_data = get_plugin_data()


class DataException(Exception):
    """数据异常"""

    pass


class ParameterException(Exception):
    """参数异常"""

    pass


class AuthException(Exception):
    """认证异常"""

    pass


class FFLogs:
    def __init__(self):
        self.base_url = "https://cn.fflogs.com/v1"

        # 定时缓存任务
        self._cache_job = None

    async def init(self) -> None:
        """初始化"""
        enable = await plugin_data.config.get("cache_enable", False)
        if enable:
            await self.enable_cache()

    async def enable_cache(self) -> None:
        """开启定时缓存任务"""
        await plugin_data.config.set("cache_enable", True)
        self._cache_job = scheduler.add_job(
            self.cache_data,
            "cron",
            hour=plugin_config.fflogs_cache_time.hour,
            minute=plugin_config.fflogs_cache_time.minute,
            second=plugin_config.fflogs_cache_time.second,
            id="fflogs_cache",
        )
        logger.info(f"开启定时缓存，执行时间为每天 {plugin_config.fflogs_cache_time}")

    async def disable_cache(self) -> None:
        """关闭定时缓存任务"""
        await plugin_data.config.set("cache_enable", False)
        if self._cache_job:
            self._cache_job.remove()
        self._cache_job = None
        logger.info("定时缓存已关闭")

    @property
    def is_cache_enabled(self) -> bool:
        """是否启用定时缓存"""
        if self._cache_job:
            return True
        else:
            return False

    async def get_token(self) -> str:
        """获取 token"""
        token = await plugin_data.config.get("token", "")
        if not token:
            raise AuthException("没有设置 token")
        return token

    async def set_character(
        self, platform: str, user_id: str, character_name: str, server_name: str
    ) -> None:
        """设置角色名和服务器名"""
        async with create_session() as session:
            await session.merge(
                User(
                    platform=platform,
                    user_id=user_id,
                    character_name=character_name,
                    server_name=server_name,
                )
            )
            await session.commit()

    async def get_character(self, platform: str, user_id: str) -> User | None:
        """获取角色名和服务器名"""
        async with create_session() as session:
            user = await session.scalar(
                select(User)
                .where(User.platform == platform)
                .where(User.user_id == user_id)
            )
            return user

    async def cache_data(self) -> None:
        """缓存数据"""
        data = await FFLOGS_DATA.data
        data = cast(FFlogsDataModel, data)
        cache_boss = await plugin_data.config.get("cache_boss", [])
        for boss in cache_boss:
            for job in data.job:
                await self.dps(boss, job.name)
                logger.info(f"{boss} {job.name}的数据缓存完成。")
                await asyncio.sleep(randint(1, 30))

    async def _http(self, url: str, params: dict = {}):
        try:
            params.setdefault("api_key", await self.get_token())
            # 使用 httpx 库发送最终的请求
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 401:
                    raise AuthException("Token 有误，无法获取数据")
                if resp.status_code == 400:
                    raise ParameterException("参数有误，无法获取数据")
                if resp.status_code != 200:
                    # 如果 HTTP 响应状态码不是 200，说明调用失败
                    return None
                return json.loads(resp.text)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError):
            # 抛出上面任何异常，说明调用失败
            return None

    async def _get_one_day_ranking(
        self, boss: int, difficulty: int, job: int, date: datetime
    ) -> list[Ranking]:
        """获取指定 boss，指定职业，指定一天中的排名数据"""
        # 查看是否有缓存
        cache_name = f'{boss}_{difficulty}_{job}_{date.strftime("%Y%m%d")}.pkl'
        if plugin_data.exists(cache_name, cache=True):
            data = plugin_data.load_pkl(cache_name, cache=True)
            # 为了兼容以前的数据，以前的数据是字典格式
            if len(data) > 0 and isinstance(data[0], dict):
                return parse_obj_as(list[Ranking], data)
            return data

        page = 1
        hasMorePages = True
        rankings: list[Ranking] = []

        end_date = date + timedelta(days=1)
        # 转换成 API 支持的时间戳格式
        start_timestamp = int(date.timestamp()) * 1000
        end_timestamp = int(end_date.timestamp()) * 1000

        # API 只支持获取 50 页以内的数据
        while hasMorePages and page < 51:
            rankings_url = f"{self.base_url}/rankings/encounter/{boss}"

            res = await self._http(
                rankings_url,
                params={
                    "metric": "rdps",
                    "difficulty": difficulty,
                    "spec": job,
                    "page": page,
                    "filter": f"date.{start_timestamp}.{end_timestamp}",
                },
            )
            try:
                ranking = FFLogsRanking.parse_obj(res)
            except ValidationError:
                raise DataException("服务器没有正确返回数据")

            hasMorePages = ranking.hasMorePages
            rankings += ranking.rankings
            page += 1

        # 如果获取数据的日期不是当天，则缓存数据
        # 因为今天的数据可能还会增加，不能先缓存
        if end_date < datetime.now():
            # 为了兼容以前的版本，这里将数据转换成 dict
            plugin_data.dump_pkl(rankings, cache_name, cache=True)

        return rankings

    async def _get_whole_ranking(
        self,
        boss: int,
        difficulty: int,
        job: int,
        dps_type: Literal["rdps", "adps", "pdps", "ndps"],
        date: datetime,
    ) -> list[float]:
        date = datetime(year=date.year, month=date.month, day=date.day)

        rankings: list[Ranking] = []
        for _ in range(plugin_config.fflogs_range):
            rankings += await self._get_one_day_ranking(boss, difficulty, job, date)
            date -= timedelta(days=1)

        # 根据 DPS 类型进行排序，并提取数据
        dps_rankings = []
        if dps_type == "rdps":
            rankings.sort(key=lambda x: x.rDPS, reverse=True)
            dps_rankings = [i.rDPS for i in rankings]

        if dps_type == "adps":
            rankings.sort(key=lambda x: x.aDPS, reverse=True)
            dps_rankings = [i.aDPS for i in rankings]

        if dps_type == "pdps":
            rankings.sort(key=lambda x: x.pDPS, reverse=True)
            dps_rankings = [i.pDPS for i in rankings]

        if dps_type == "ndps":
            rankings.sort(key=lambda x: x.nDPS, reverse=True)
            dps_rankings = [i.nDPS for i in rankings]

        if not dps_rankings:
            raise DataException("网站里没有数据")

        return dps_rankings

    async def _get_character_ranking(
        self,
        characterName: str,
        serverName: str,
        zone: int,
        encounter: int,
        difficulty: int,
        metric: Literal["rdps", "adps", "pdps", "ndps"],
    ):
        """查询指定角色的 DPS

        返回列表
        """
        url = f"https://cn.fflogs.com/v1/rankings/character/{characterName}/{serverName}/CN"

        res = await self._http(
            url,
            params={
                "zone": zone,
                "encounter": encounter,
                "metric": metric,
            },
        )

        if not res and isinstance(res, list):
            raise DataException("网站里没有数据")

        if not res:
            raise DataException("获取数据失败")

        if "hidden" in res:
            raise DataException("角色数据被隐藏")

        try:
            rankings = parse_obj_as(list[CharacterRanking], res)
        except ValidationError:
            raise DataException("服务器没有正确返回数据")

        # 提取所需的数据
        # 零式副本的难度是 101，普通的则是 100
        # 极神也是 100
        if difficulty == 0:
            ranking = [i for i in rankings if i.difficulty == 101]
        else:
            ranking = [i for i in rankings if i.difficulty == 100]

        if not ranking:
            raise DataException("网站里没有数据")

        return ranking

    async def zones(self) -> list[Zones]:
        """副本"""
        url = f"{self.base_url}/zones"
        data = await self._http(url)
        zones = parse_obj_as(list[Zones], data)
        return zones

    async def classes(self) -> list[Class]:
        """职业"""
        url = f"{self.base_url}/classes"
        data = await self._http(url)
        classes = parse_obj_as(list[Class], data)
        return classes

    async def dps(
        self,
        boss_nickname: str,
        job_nickname: str,
        dps_type: Literal["rdps", "adps", "pdps", "ndps"] = "rdps",
    ) -> str:
        """查询 DPS 百分比排名

        :param boss_nickname: BOSS 的称呼
        :param job_nickname: 职业的称呼
        :param dps_type: DPS 的种类，支持 rdps, adps, pdps (Default value = 'rdps')
        """
        boss = await get_boss_info_by_nickname(boss_nickname)
        if not boss:
            return f"找不到 {boss_nickname} 的数据，请换个名字试试"

        job = await get_job_info_by_nickname(job_nickname)
        if not job:
            return f"找不到 {job_nickname} 的数据，请换个名字试试"

        if dps_type not in ["adps", "rdps", "pdps", "ndps"]:
            return f"找不到类型为 {dps_type} 的数据，只支持 adps rdps pdps ndps"

        # 排名从前一天开始排，因为今天的数据并不全
        date = datetime.now() - timedelta(days=1)
        try:
            rankings = await self._get_whole_ranking(
                boss.encounter, boss.difficulty, job.spec, dps_type, date
            )
        except DataException as e:
            return f"{e}，请稍后再试"

        reply = f"{boss.name} {job.name} 的数据({dps_type})"

        total = len(rankings)
        reply += f"\n数据总数：{total} 条"
        # 计算百分比的 DPS
        percentage_list = [100, 99, 95, 75, 50, 25, 10]
        for perc in percentage_list:
            number = math.floor(total * 0.01 * (100 - perc))
            dps_value = float(rankings[number])
            reply += f"\n{perc}% : {dps_value:.2f}"

        return reply

    async def character_dps(
        self,
        boss_nickname: str,
        character_name: str,
        server_name: str,
        dps_type: Literal["rdps", "adps", "pdps"] = "rdps",
    ) -> str:
        """查询指定角色在某个副本的 DPS

        :param boss_nickname: BOSS 的称呼
        :param character_name: 角色名
        :param server_name: 服务器名
        :param dps_type: DPS 的种类，支持 rdps, adps (Default value = 'rdps')
        """
        boss = await get_boss_info_by_nickname(boss_nickname)
        if not boss:
            return f"找不到 {boss_nickname} 的数据，请换个名字试试"
        reply = f"{boss.name} {character_name}-{server_name} 的排名({dps_type})"

        try:
            ranking = await self._get_character_ranking(
                character_name,
                server_name,
                boss.zone,
                boss.encounter,
                boss.difficulty,
                dps_type,
            )
        except DataException as e:
            return f"{e}，请稍后再试"
        except ParameterException:
            return "角色名或者服务器名有误，无法获取数据。"

        for i in ranking:
            reply += f"\n{i.spec} {i.percentile:.2f}% {i.total:.2f}"

        return reply


fflogs = FFLogs()
post_db_init(fflogs.init)
