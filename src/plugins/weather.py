'''天气插件'''
import json
import re
import urllib

import requests

from coolqbot.bot import bot
from coolqbot.logger import logger


@bot.on_message('group')
async def weather(context):
    match = re.match(r'^\/天气 ?(\w*)?', context['message'])
    if match:
        city = match.group(1)
        str_data = weather_old(city)
        if not str_data:
            str_data = weather_extend(city)
        if not str_data:
            str_data = '我才不是因为不知道才不告诉你{}的天气呢'.format(city)
        return {'reply': str_data, 'at_sender': False}


KEY1 = '31662bc776555612e3639dbca1ad1fd5'


def weather_old(city):
    '''百度天气'''
    try:
        city_name = urllib.parse.quote(city.encode('utf-8'))
        url_str = f'http://api.map.baidu.com/telematics/v3/weather?location={city_name}&ak={KEY1}&output=json'
        response = requests.get(url_str)
        data = response.content.decode('utf-8')
        json_result = json.loads(data)['results'][0]
        str_data = ''
        str_data += json_result['currentCity'] + \
            ' PM:' + json_result['pm25'] + '\n'
        try:
            str_data += json_result['index'][0]['des'] + '\n'
        except:
            pass

        for data in json_result['weather_data']:
            str_data += data['date'] + ' '
            str_data += data['weather'] + ' '
            str_data += data['wind'] + ' '
            str_data += data['temperature']
            str_data += '\n'

        return str_data
    except Exception as e:
        logger.warning(e)
        return None


KEY2 = '6ff5a040195245328b3cdc693d1c0bb2'


def weather_extend(city):
    '''
    和风天气API
    日本 东京
    当前温度：25(体感温度：29)
    2018-08-13 中雨 降水概率：0 温度：26~32℃
    2018-08-14 小雨 降水概率：13 温度：26~33℃
    2018-08-15 小雨 降水概率：11 温度：25~32℃

    '''
    try:
        city_name = urllib.parse.quote(city.encode('utf-8'))
        url_str = f'https://free-api.heweather.com/s6/weather?location={city_name}&key={KEY2}'
        response = requests.get(url_str)
        data = response.content.decode('utf-8')
        weather_result = json.loads(data)['HeWeather6'][0]
        weather_basic = weather_result['basic']
        weather_now = weather_result['now']
        weather_forecast = weather_result['daily_forecast']

        str_data = weather_basic['cnty'] + ' ' + \
            weather_basic['location'] + '\n' # 中国 成都

        #{weather_now[""]}
        str_data += f'当前温度：{weather_now["tmp"]}(体感温度：{weather_now["fl"]})\n'

        #{forecast[""]}
        for forecast in weather_forecast:
            str_data += f'{forecast["date"]} {forecast["cond_txt_d"]} 降水概率：{forecast["pop"]} 温度：{forecast["tmp_min"]}~{forecast["tmp_max"]}℃\n'

        return str_data
    except Exception as e:
        logger.exception(e)
        return None
