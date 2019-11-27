""" API

文档网址 https://cn.fflogs.com/v1/docs
"""
import json
import math
import re
from datetime import datetime, timedelta

import aiohttp

from coolqbot import PluginData

from .data import get_boss_info, get_job_name


class FFlogs:
    def __init__(self):
        self.base_url = 'https://cn.fflogs.com/v1'
        self.data = PluginData('fflogs', config=True)

        # 当前是 5.0 版本
        self.version = self.data.config_get('fflogs', 'version', '0')
        # 默认为两周的数据
        self.range = int(self.data.config_get('fflogs', 'range', '14'))

    @property
    def token(self):
        try:
            return self.data.config_get('fflogs', 'token')
        except:
            return None

    @token.setter
    def token(self, token):
        self.data.config_set('fflogs', 'token', token)

    async def _http(self, url, is_json=True, headers=None):
        try:
            # 使用 aiohttp 库发送最终的请求
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, headers=headers) as response:
                    if response.status != 200:
                        # 如果 HTTP 响应状态码不是 200，说明调用失败
                        return None
                    if is_json:
                        resp_payload = json.loads(await response.text())
                    else:
                        resp_payload = await response.text()

                    return resp_payload
        except (aiohttp.ClientError, json.JSONDecodeError, KeyError):
            # 抛出上面任何异常，说明调用失败
            return None

    def _find_ranking_cache(self, boss, difficulty, job, dps_type, date):
        """ 查找是否缓存了此数据
        """
        name = f'{boss}_{difficulty}_{job}_{dps_type}_{date[0]}_{date[1]}'
        if self.data.exists(f'{name}.pkl'):
            return self.data.load_pkl(name)
        return None

    def _save_ranking_cache(self, boss, difficulty, job, dps_type, date, data):
        """ 缓存数据
        """
        name = f'{boss}_{difficulty}_{job}_{dps_type}_{date[0]}_{date[1]}'
        self.data.save_pkl(data, name)

    async def _get_all_ranking(self, boss, difficulty, job, dps_type, date):
        """ 获取指定 boss，指定职业，指定时间的所有排名数据
        """
        if dps_type == 'adps':
            dps_type = 'dps'

        # 查看是否有缓存
        rankings = self._find_ranking_cache(boss, difficulty, job, dps_type, date)
        if rankings:
            return rankings

        page = 1
        hasMorePages = True
        rankings = []

        while hasMorePages:
            rankings_url = f'{self.base_url}/rankings/encounter/{boss}?metric={dps_type}&difficulty={difficulty}&spec={job}&page={page}&filter=date.{date[0]}.{date[1]}&api_key={self.token}'
            res = await self._http(rankings_url)
            hasMorePages = res['hasMorePages']
            rankings += res['rankings']
            page += 1

        # 缓存数据
        self._save_ranking_cache(boss, difficulty, job, dps_type, date, rankings)

        return rankings

    async def zones(self):
        """ 副本
        """
        url = f'{self.base_url}/zones?api_key={self.token}'
        data = await self._http(url)
        return data

    async def classes(self):
        """ 职业
        """
        url = f'{self.base_url}/classes?api_key={self.token}'
        data = await self._http(url)
        return data

    async def dps(self, boss, job, dps_type='rdps'):
        """ 查询 DPS 百分比排名
        """
        boss_id, difficulty, boss_name = get_boss_info(boss)
        if not boss_id:
            return f'找不到 {boss} 的数据，请换个名字试试'

        job_id, job_name = get_job_name(job)
        if not job_id:
            return f'找不到 {job} 的数据，请换个名字试试'

        if dps_type not in ['adps', 'rdps']:
            return f'找不到类型为 {dps_type} 的数据，现在只支持 adps rdps'

        # 日期应该是今天 24 点前开始计算
        now = datetime.now()
        end_date = datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=23,
            minute=59,
            second=59
        )
        start_date = end_date - timedelta(days=self.range)
        start_date = int(start_date.timestamp()) * 1000
        end_date = int(end_date.timestamp()) * 1000

        rankings = await self._get_all_ranking(
            boss_id, difficulty, job_id, dps_type, (start_date, end_date)
        )

        reply = f'{boss_name} {job_name} 的数据({dps_type})'

        # 计算百分比的 DPS
        total = len(rankings)
        percentage_list = [100, 99, 95, 75, 50, 25, 10]
        for perc in percentage_list:
            number = math.floor(total * 0.01 * (100 - perc))
            dps = float(rankings[number]['total'])
            reply += f'\n{perc}% : {dps:.2f}'

        return reply


API = FFlogs()
