""" API

文档网址 https://cn.fflogs.com/v1/docs
"""
import json
import math
from datetime import datetime, timedelta

import aiohttp

from coolqbot import PluginData

from .data import get_boss_info, get_job_name
from .exceptions import AuthException, DataException, ParameterException


class FFLogs:
    def __init__(self):
        self.base_url = 'https://cn.fflogs.com/v1'
        self.data = PluginData('fflogs', config=True)

        # Token
        self._token = None

        # 默认从两周的数据中计算排名百分比
        self.range = int(self.data.config_get('fflogs', 'range', '14'))

        # QQ号 与 最终幻想14 角色用户名，服务器的对应关系
        if self.data.exists('characters.pkl'):
            self.characters = self.data.load_pkl('characters')
        else:
            self.characters = {}

    @property
    def token(self):
        if not self._token:
            self._token = self.data.config_get('fflogs', 'token')
        return self._token

    @token.setter
    def token(self, token):
        self.data.config_set('fflogs', 'token', token)
        self._token = token

    async def _http(self, url, is_json=True, headers=None):
        try:
            # 使用 aiohttp 库发送最终的请求
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, headers=headers) as response:
                    if response.status == 401:
                        raise AuthException('Token 有误，无法获取数据')
                    if response.status == 400:
                        raise ParameterException('参数有误，无法获取数据')
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

    async def _get_one_day_ranking(
        self, boss, difficulty, job, date: datetime
    ):
        """ 获取指定 boss，指定职业，指定一天中的排名数据
        """
        # 查看是否有缓存
        cache_name = f'{boss}_{difficulty}_{job}_{date.strftime("%Y%m%d")}'
        if self.data.exists(f'{cache_name}.pkl'):
            return self.data.load_pkl(cache_name)

        page = 1
        hasMorePages = True
        rankings = []

        end_date = date + timedelta(days=1)
        # 转换成 API 支持的时间戳格式
        start_timestamp = int(date.timestamp()) * 1000
        end_timestamp = int(end_date.timestamp()) * 1000

        # API 只支持获取 50 页以内的数据
        while hasMorePages and page < 51:
            rankings_url = f'{self.base_url}/rankings/encounter/{boss}?metric=rdps&difficulty={difficulty}&spec={job}&page={page}&filter=date.{start_timestamp}.{end_timestamp}&api_key={self.token}'

            res = await self._http(rankings_url)

            if not res:
                raise DataException('服务器没有正确返回数据')

            hasMorePages = res['hasMorePages']
            rankings += res['rankings']
            page += 1

        # 如果获取数据的日期不是当天，则缓存数据
        # 因为今天的数据可能还会增加，不能先缓存
        if end_date < datetime.now():
            self.data.save_pkl(rankings, cache_name)

        return rankings

    async def _get_whole_ranking(
        self, boss, difficulty, job, dps_type: str, date: datetime
    ):
        date = datetime(year=date.year, month=date.month, day=date.day)

        rankings = []
        for _ in range(self.range):
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
        url = f'https://cn.fflogs.com/v1/rankings/character/{characterName}/{serverName}/CN?zone={zone}&encounter={encounter}&metric={metric}&api_key={self.token}'

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
        return ranking

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
        boss_zone, boss_id, difficulty, boss_name = get_boss_info(boss)
        if not boss_id:
            return f'找不到 {boss} 的数据，请换个名字试试'

        job_id, job_name = get_job_name(job)
        if not job_id:
            return f'找不到 {job} 的数据，请换个名字试试'

        if dps_type not in ['adps', 'rdps', 'pdps']:
            return f'找不到类型为 {dps_type} 的数据，只支持 adps rdps pdps'

        # 排名从前一天开始排，因为今天的数据并不全
        date = datetime.now() - timedelta(days=1)
        try:
            rankings = await self._get_whole_ranking(
                boss_id, difficulty, job_id, dps_type, date
            )
        except DataException as e:
            return f'{e}，请稍后再试'

        reply = f'{boss_name} {job_name} 的数据({dps_type})'

        total = len(rankings)
        reply += f'\n数据总数：{total} 条'
        # 计算百分比的 DPS
        percentage_list = [100, 99, 95, 75, 50, 25, 10]
        for perc in percentage_list:
            number = math.floor(total * 0.01 * (100 - perc))
            dps = float(rankings[number])
            reply += f'\n{perc}% : {dps:.2f}'

        return reply

    def set_character(self, user_id, character_name, server_name):
        """ 设置 QQ号 与 最终幻想14 用户名和服务器名
        """
        self.characters[user_id] = [character_name, server_name]
        self.data.save_pkl(self.characters, 'characters')

    async def character_dps(
        self, boss, character_name, server_name, dps_type='rdps'
    ):
        """ 查询指定角色的 DPS
        """
        boss_zone, boss_id, difficulty, boss_name = get_boss_info(boss)
        if not boss_id:
            return f'找不到 {boss} 的数据，请换个名字试试'
        reply = f'{boss_name} {character_name}-{server_name} 的排名({dps_type})'

        try:
            ranking = await self._get_character_ranking(
                character_name, server_name, boss_zone, boss_id, difficulty,
                dps_type
            )
        except DataException as e:
            return f'{e}，请稍后再试'
        except ParameterException:
            return '角色名或者服务器名有误，无法获取数据。'

        for i in ranking:
            reply += f'\n{i["spec"]} {i["percentile"]}% {i["total"]:.2f}'

        return reply


API = FFLogs()
