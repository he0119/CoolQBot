""" API
"""
import json
import re

import aiohttp

from coolqbot import PluginData
from .data import get_boss_info, get_job_name


class FFlogs:
    def __init__(self):
        self.base_url = 'https://cn.fflogs.com/v1'
        self.data = PluginData('fflogs', config=True)

        self.token = self.get_token()
        # 当前是 5.0 版本
        self.version = self.data.config_get('fflogs', 'version', '0')
        # 默认为两周的数据
        self.range = self.data.config_get('fflogs', 'range', '14')

    def set_token(self, token):
        self.token = token
        self.data.config_set('fflogs', 'token', self.token)

    def get_token(self):
        try:
            return self.data.config_get('fflogs', 'token')
        except:
            return None

    async def _http(self, url, is_json=True):
        try:
            # 使用 aiohttp 库发送最终的请求
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url) as response:
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

    async def zones(self):
        """ 副本
        """
        url = f'{self.base_url}/zones?api_key={self.token}'
        data = await self._http(url)
        return data

    async def dps(self, boss, job, dps_type='rdps'):
        """ 查询 DPS 百分比排名
        """
        (boss_bucket, boss_id), boss_name = get_boss_info(boss)
        if not boss_bucket:
            return f'找不到 {boss} 的数据，请换个名字试试'

        job_name_en, job_name_cn = get_job_name(job)
        if not job_name_en:
            return f'找不到 {job} 的数据，请换个名字试试'

        fflogs_url = f'https://cn.fflogs.com/zone/statistics/table/{boss_bucket}/dps/{boss_id}/100/8/5/100/1/{self.range}/{self.version}/Global/{job_name_en}/All/0/normalized/single/0/-1/?keystone=15&dpstype={dps_type}'

        res = await self._http(fflogs_url, is_json=False)

        percentage_list = [100, 99, 95, 75, 50, 25, 10]
        reply = f'{boss_name} {job_name_cn} 的数据({dps_type})'
        for perc in percentage_list:
            if perc == 100:
                re_str = ('series' + r'.data.push\((\d*\.?\d*)\)')
            else:
                re_str = (f'series{perc}' + r'.data.push\((\d*\.?\d*)\)')
            ptn = re.compile(re_str)
            find_res = float(ptn.findall(res)[0])
            reply += f'\n{perc}% : {find_res:.2f}'
        return reply


API = FFlogs()
