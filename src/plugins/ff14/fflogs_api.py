""" FFLogs API

v1 版的 API，现在已经废弃，不没有维护
以后可能会失效
文档网址 https://cn.fflogs.com/v1/docs
"""
import asyncio
import json
import math
from datetime import datetime, timedelta

import httpx
from nonebot.log import logger
from nonebot.sched import scheduler

from .config import DATA, config
from .fflogs_data import (
    get_boss_info_by_nickname, get_job_info_by_nickname, get_jobs_info
)


class DataException(Exception):
    """ 数据异常 """
    pass


class ParameterException(Exception):
    """ 参数异常 """
    pass


class AuthException(Exception):
    """ 认证异常 """
    pass


class FFLogs:
    def __init__(self):
        self.base_url = 'https://cn.fflogs.com/v1'

        # 定时缓存任务
        self._cache_job = None

        # 根据配置启动
        if config.fflogs_cache:
            self.enable_cache()

        # QQ号 与 最终幻想14 角色用户名，服务器的对应关系
        if DATA.exists('characters.pkl'):
            self.characters = DATA.load_pkl('characters')
        else:
            self.characters = {}

    def enable_cache(self):
        """ 开启定时缓存任务 """
        self._cache_job = scheduler.add_job(
            self.cache_data,
            'cron',
            hour=config.fflogs_cache_hour,
            minute=config.fflogs_cache_minute,
            second=config.fflogs_cache_second,
            id='fflogs_cache'
        )
        config.fflogs_cache = True
        logger.info(
            f'开启定时缓存，执行时间为每天 {config.fflogs_cache_hour}:{config.fflogs_cache_minute}:{config.fflogs_cache_second}'
        )

    def disable_cache(self):
        """ 关闭定时缓存任务 """
        self._cache_job.remove()
        self._cache_job = None
        config.fflogs_cache = False
        logger.info('定时缓存已关闭')

    @property
    def is_cache_enabled(self):
        """ 是否启用定时缓存 """
        if self._cache_job:
            return True
        else:
            return False

    async def cache_data(self):
        jobs = get_jobs_info()
        for boss in config.fflogs_cache_boss:
            for job in jobs:
                await self.dps(boss, job.name)
                logger.info(f'{boss} {job.name}的数据缓存完成。')
                await asyncio.sleep(30)

    @staticmethod
    async def _http(url):
        try:
            # 使用 httpx 库发送最终的请求
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                if resp.status_code == 401:
                    raise AuthException('Token 有误，无法获取数据')
                if resp.status_code == 400:
                    raise ParameterException('参数有误，无法获取数据')
                if resp.status_code != 200:
                    # 如果 HTTP 响应状态码不是 200，说明调用失败
                    return None
                return json.loads(resp.text)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError):
            # 抛出上面任何异常，说明调用失败
            return None

    async def _get_one_day_ranking(
        self, boss, difficulty, job, date: datetime
    ):
        """ 获取指定 boss，指定职业，指定一天中的排名数据
        """
        # 查看是否有缓存
        cache_name = f'{boss}_{difficulty}_{job}_{date.strftime("%Y%m%d")}'
        if DATA.exists(f'{cache_name}.pkl'):
            return DATA.load_pkl(cache_name)

        page = 1
        hasMorePages = True
        rankings = []

        end_date = date + timedelta(days=1)
        # 转换成 API 支持的时间戳格式
        start_timestamp = int(date.timestamp()) * 1000
        end_timestamp = int(end_date.timestamp()) * 1000

        # API 只支持获取 50 页以内的数据
        while hasMorePages and page < 51:
            rankings_url = f'{self.base_url}/rankings/encounter/{boss}?metric=rdps&difficulty={difficulty}&spec={job}&page={page}&filter=date.{start_timestamp}.{end_timestamp}&api_key={config.fflogs_token}'

            res = await self._http(rankings_url)

            if not res:
                raise DataException('服务器没有正确返回数据')

            hasMorePages = res['hasMorePages']
            rankings += res['rankings']
            page += 1

        # 如果获取数据的日期不是当天，则缓存数据
        # 因为今天的数据可能还会增加，不能先缓存
        if end_date < datetime.now():
            DATA.save_pkl(rankings, cache_name)

        return rankings

    async def _get_whole_ranking(
        self, boss, difficulty, job, dps_type: str, date: datetime
    ):
        date = datetime(year=date.year, month=date.month, day=date.day)

        rankings = []
        for _ in range(config.fflogs_range):
            rankings += await self._get_one_day_ranking(
                boss, difficulty, job, date
            )
            date -= timedelta(days=1)

        # 根据 DPS 类型进行排序，并提取数据
        if dps_type == 'rdps':
            rankings.sort(key=lambda x: x['total'], reverse=True)
            rankings = [i['total'] for i in rankings]

        if dps_type == 'adps':
            rankings.sort(
                key=lambda x: x['other_per_second_amount'], reverse=True
            )
            rankings = [i['other_per_second_amount'] for i in rankings]

        if dps_type == 'pdps':
            rankings.sort(key=lambda x: x['raw_dps'], reverse=True)
            rankings = [i['raw_dps'] for i in rankings]

        if not rankings:
            raise DataException('网站里没有数据')

        return rankings

    async def _get_character_ranking(
        self, characterName, serverName, zone, encounter, difficulty, metric
    ):
        """ 查询指定角色的 DPS

        返回列表
        """
        url = f'https://cn.fflogs.com/v1/rankings/character/{characterName}/{serverName}/CN?zone={zone}&encounter={encounter}&metric={metric}&api_key={config.fflogs_token}'

        res = await self._http(url)

        if not res and isinstance(res, list):
            raise DataException('网站里没有数据')

        if not res:
            raise DataException('获取数据失败')

        if 'hidden' in res:
            raise DataException('角色数据被隐藏')

        # 提取所需的数据
        # 零式副本的难度是 101，普通的则是 100
        # 极神也是 100
        if difficulty == 0:
            ranking = [i for i in res if i['difficulty'] == 101]
        else:
            ranking = [i for i in res if i['difficulty'] == 100]

        if not ranking:
            raise DataException('网站里没有数据')

        return ranking

    async def zones(self):
        """ 副本 """
        url = f'{self.base_url}/zones?api_key={config.fflogs_token}'
        data = await self._http(url)
        return data

    async def classes(self):
        """ 职业 """
        url = f'{self.base_url}/classes?api_key={config.fflogs_token}'
        data = await self._http(url)
        return data

    async def dps(self, boss_nickname, job_nickname, dps_type='rdps'):
        """ 查询 DPS 百分比排名

        :param boss_nickname: BOSS 的称呼
        :param job_nickname: 职业的称呼
        :param dps_type: DPS 的种类，支持 rdps, adps, pdps (Default value = 'rdps')
        """
        boss = get_boss_info_by_nickname(boss_nickname)
        if not boss:
            return f'找不到 {boss_nickname} 的数据，请换个名字试试'

        job = get_job_info_by_nickname(job_nickname)
        if not job:
            return f'找不到 {job_nickname} 的数据，请换个名字试试'

        if dps_type not in ['adps', 'rdps', 'pdps']:
            return f'找不到类型为 {dps_type} 的数据，只支持 adps rdps pdps'

        # 排名从前一天开始排，因为今天的数据并不全
        date = datetime.now() - timedelta(days=1)
        try:
            rankings = await self._get_whole_ranking(
                boss.encounter, boss.difficulty, job.spec, dps_type, date
            )
        except DataException as e:
            return f'{e}，请稍后再试'

        reply = f'{boss.name} {job.name} 的数据({dps_type})'

        total = len(rankings)
        reply += f'\n数据总数：{total} 条'
        # 计算百分比的 DPS
        percentage_list = [100, 99, 95, 75, 50, 25, 10]
        for perc in percentage_list:
            number = math.floor(total * 0.01 * (100 - perc))
            dps_value = float(rankings[number])
            reply += f'\n{perc}% : {dps_value:.2f}'

        return reply

    def set_character(self, user_id, character_name, server_name) -> None:
        """ 设置 QQ号 与 最终幻想14 用户名和服务器名
        """
        self.characters[user_id] = [character_name, server_name]
        DATA.save_pkl(self.characters, 'characters')

    async def character_dps(
        self,
        boss_nickname: str,
        character_name: str,
        server_name: str,
        dps_type: str = 'rdps'
    ) -> str:
        """ 查询指定角色在某个副本的 DPS

        :param boss_nickname: BOSS 的称呼
        :param character_name: 角色名
        :param server_name: 服务器名
        :param dps_type: DPS 的种类，支持 rdps, adps (Default value = 'rdps')
        """
        boss = get_boss_info_by_nickname(boss_nickname)
        if not boss:
            return f'找不到 {boss_nickname} 的数据，请换个名字试试'
        reply = f'{boss.name} {character_name}-{server_name} 的排名({dps_type})'

        try:
            ranking = await self._get_character_ranking(
                character_name, server_name, boss.zone, boss.encounter,
                boss.difficulty, dps_type
            )
        except DataException as e:
            return f'{e}，请稍后再试'
        except ParameterException:
            return '角色名或者服务器名有误，无法获取数据。'

        for i in ranking:
            reply += f'\n{i["spec"]} {i["percentile"]:.2f}% {i["total"]:.2f}'

        return reply


fflogs_api = FFLogs()
