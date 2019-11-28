""" 和风天气
"""
import json
import re
import urllib

import requests

from coolqbot import PluginData

DATA = PluginData('weather', config=True)
KEY = DATA.config_get('heweather', 'key')


def heweather(city):
    """ 和风天气 API

    日本 东京
    当前温度：25(体感温度：29)
    2018-08-13 中雨 降水概率：0% 温度：32~26℃
    2018-08-14 小雨 降水概率：13% 温度：33~26℃
    2018-08-15 小雨 降水概率：11% 温度：32~25℃
    """
    if not KEY:
        return None

    try:
        city_name = urllib.parse.quote(city.encode('utf-8'))
        url_str = f'https://free-api.heweather.com/s6/weather?location={city_name}&key={KEY}'
        response = requests.get(url_str)
        data = response.content.decode('utf-8')
        weather_result = json.loads(data)['HeWeather6'][0]
        weather_basic = weather_result['basic']
        weather_now = weather_result['now']
        weather_forecast = weather_result['daily_forecast']

        str_data = weather_basic['cnty'] + ' ' + \
            weather_basic['location'] + '\n'  # 中国 成都

        # {weather_now[""]}
        str_data += f'当前温度：{weather_now["tmp"]}(体感温度：{weather_now["fl"]})\n'

        # {forecast[""]}
        for forecast in weather_forecast:
            if forecast['cond_txt_d'] == forecast['cond_txt_n']:
                cond_text = forecast['cond_txt_d']
            else:
                cond_text = f'{forecast["cond_txt_d"]}转{forecast["cond_txt_n"]}'
            str_data += f'{forecast["date"]} {cond_text} 降水概率：{forecast["pop"]}% 温度：{forecast["tmp_max"]}~{forecast["tmp_min"]}℃\n'

        return str_data[:-1]
    except:
        return None
