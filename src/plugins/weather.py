""" 天气插件
"""
import json
import re
import urllib

import requests

from coolqbot.bot import bot


@bot.on_message('group', 'private')
async def weather(context):
    match = re.match(r'^\/(?:天气|weather)(?: (\w*))?$', context['message'])
    if match:
        city = match.group(1)
        str_data = heweather(city)
        if not str_data:
            str_data = f'我才不是因为不知道才不告诉你{city}的天气呢'
        return {'reply': str_data, 'at_sender': False}


KEY = '6ff5a040195245328b3cdc693d1c0bb2'


def heweather(city):
    """ 和风天气 API

    日本 东京
    当前温度：25(体感温度：29)
    2018-08-13 中雨 降水概率：0 温度：26~32℃
    2018-08-14 小雨 降水概率：13 温度：26~33℃
    2018-08-15 小雨 降水概率：11 温度：25~32℃
    """
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
            if forecast["cond_txt_d"] == forecast["cond_txt_n"]:
                cond_text = forecast["cond_txt_d"]
            else:
                cond_text = f'{forecast["cond_txt_d"]}转{forecast["cond_txt_n"]}'
            str_data += f'{forecast["date"]} {cond_text} 降水概率：{forecast["pop"]} 温度：{forecast["tmp_min"]}~{forecast["tmp_max"]}℃\n'

        return str_data[:-1]
    except Exception as e:
        bot.logger.exception(e)
        return None
