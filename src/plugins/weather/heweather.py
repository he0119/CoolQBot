""" 和风天气
"""
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx

from .config import plugin_config


async def get(url: str) -> Dict:
    """ 请求 API 并自动在后面加上 key """
    async with httpx.AsyncClient() as client:
        resp = await client.get(url + f'&key={plugin_config.heweather_key}')
        return resp.json()


async def lookup_location(location: str,
                          adm: Optional[str] = None
                          ) -> Optional[Tuple[str, str]]:
    """ 根据地名和行政区名查询地点的ID和展示的名称

    '101270101', '中国 四川省 成都'
    """
    params = {'location': location}
    if adm:
        params['adm'] = adm

    params = urlencode(params)

    url = f'https://geoapi.qweather.com/v2/city/lookup?{params}'
    resp = await get(url)

    if resp['code'] == '200':
        locations = [
            resp['location'][0]['country'],
            resp['location'][0]['adm1'],
            resp['location'][0]['adm2'],
            resp['location'][0]['name'],
        ]

        # 去重，依据优先级
        # 从 国家 第一级行政区 第二集行政区 地名 来
        filtered = []
        for location in locations:
            if location not in filtered:
                filtered.append(location)

        return resp['location'][0]['id'], ' '.join(filtered)


async def now(location_id: str) -> str:
    """ 获取实时天气

    当前温度：19℃ 湿度：35%(体感温度：17℃)
    """
    url = f'https://devapi.qweather.com/v7/weather/now?location={location_id}'
    resp = await get(url)

    temp = resp['now']['temp']
    humidity = resp['now']['humidity']
    feelsLike = resp['now']['feelsLike']

    return f'当前温度：{temp}℃ 湿度：{humidity}%(体感温度：{feelsLike}℃)'


async def daily(location_id: str) -> str:
    """ 获取今后三天的天气

    2020-11-18 多云转阴 温度：20~12℃
    2020-11-19 晴转多云 温度：20~12℃
    2020-11-20 多云转小雨 温度：18~12℃
    """
    url = f'https://devapi.qweather.com/v7/weather/3d?location={location_id}'
    resp = await get(url)

    daily_text = []
    for day in resp['daily']:
        temp_text = [day['fxDate']]
        if day['textDay'] == day['textNight']:
            temp_text.append(day['textDay'])
        else:
            temp_text.append(f'{day["textDay"]}转{day["textNight"]}')
        if 'pop' in day:
            temp_text.append(f'降水概率：{day["pop"]}%')
        temp_text.append(f'温度：{day["tempMax"]}~{day["tempMin"]}℃')
        daily_text.append(' '.join(temp_text))
    return '\n'.join(daily_text)


async def heweather(location: str, adm: Optional[str] = None) -> Optional[str]:
    """ 和风天气 API

    日本 东京
    当前温度：25(体感温度：29)
    2018-08-13 中雨 降水概率：0% 温度：32~26℃
    2018-08-14 小雨 降水概率：13% 温度：33~26℃
    2018-08-15 小雨 降水概率：11% 温度：32~25℃
    """
    if not plugin_config.heweather_key:
        return None

    try:
        city = await lookup_location(location, adm)
        if not city:
            return None

        return '\n'.join(
            [
                city[1],
                await now(city[0]),
                await daily(city[0]),
            ]
        )

    except:
        return None
