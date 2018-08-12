import json
import re
import urllib
from datetime import datetime, timedelta
from random import randint

import requests
import websocket
from websocket import create_connection

# =====复读插件=====


class Recorder(object):
    def __init__(self):
        self.last_message_on = datetime.utcnow()


recorder = Recorder()


def is_repeat(recorder, msg):
    if msg['group_id'] != 438789224:
        return False

    # 不要复读图片，签到，分享
    match = re.match(r'^\[CQ:(image|sign|share).+\]', msg['message'])
    if match:
        return False

    # 不要复读指令
    match = re.match(r'^\/|!', msg['message'])
    if match:
        return False

    rand = randint(1, 100)
    print(rand)
    if rand > 15:
        return False

    time = recorder.last_message_on
    if datetime.utcnow() < time + timedelta(minutes=1):
        return False
    recorder.last_message_on = datetime.utcnow()

    return True


def repeat(msg):
    global recorder
    if is_repeat(recorder, msg):
        send_group_msg(msg['message'])

# =====掷骰子=====


def rand(msg):
    match = re.match(r'^\/rand ?(\w*)?', msg['message'])
    if match:
        args = match.group(1)
        str_data = f'[CQ:at,qq={msg["user_id"]}]'

        probability = re.match(r'\w+(可能性|几率|概率)$', args)
        if probability:
            str_data += ' '
            str_data += args
            str_data += '是 '
            str_data += str(randint(0, 100))
            str_data += '%'
        else:
            str_data += ' 你的点数是 '
            str_data += str(randint(0, 100))

        send_group_msg(str_data)

# =====bilibili=====


def bilibili_today(msg):
    match = re.match(r'^\/bilibili', msg['message'])
    if match:
        try:
            output = ''
            response = requests.get(
                "https://bangumi.bilibili.com/web_api/timeline_global")
            data = response.content.decode('utf-8')
            rjson = json.loads(data)
            for day in rjson['result']:
                if(day['is_today'] == 1):
                    for item in day['seasons']:
                        output += item['pub_time'] + \
                            " : " + item['title'] + "\n"
            send_group_msg(output)
        except:
            send_group_msg("获取番剧信息失败了~>_<~")

# =====天气插件=====


KEY1 = '31662bc776555612e3639dbca1ad1fd5'


def weather_old(city):
    '''百度天气'''
    try:
        city_name = urllib.parse.quote(city.encode('utf-8'))
        url_str = "http://api.map.baidu.com/telematics/v3/weather?location={city}&ak={key}&output=json".format(
            city=city_name,
            key=KEY1
        )
        response = requests.get(url_str)
        data = response.content.decode('utf-8')
        json_result = json.loads(data)['results'][0]

        str_data = ''
        str_data += json_result['currentCity'] + \
            " PM:" + json_result['pm25'] + "\n"
        try:
            str_data += json_result["index"][0]['des'] + "\n"
        except:
            pass

        for data in json_result["weather_data"]:
            str_data += data['date'] + " "
            str_data += data['weather'] + " "
            str_data += data['wind'] + " "
            str_data += data['temperature']
            str_data += '\n'

        return str_data
    except Exception as e:
        print(e)
        return None


KEY2 = '6ff5a040195245328b3cdc693d1c0bb2'


def weather_extend(city):
    '''
    和风天气API
    中国 长沙 PM:74
    建议着薄外套、开衫牛仔衫裤等服装。年老体弱者应适当添加衣物，宜着夹克衫、薄毛衣等。
    周四 04月26日 (实时：16℃) 阵雨转多云 西北风微风 20 ~ 15℃
    周五 多云 东北风微风 27 ~ 17℃
    周六 多云转雷阵雨 南风微风 28 ~ 21℃
    周日 阵雨 南风微风 25 ~ 21℃
    '''
    try:
        city_name = urllib.parse.quote(city.encode('utf-8'))
        url_str = "https://free-api.heweather.com/s6/weather?location={city}&key={key}".format(
            city=city_name,
            key=KEY2
        )
        response = requests.get(url_str)
        data = response.content.decode('utf-8')
        weather_result = json.loads(data)['HeWeather6'][0]
        weather_basic = weather_result['basic']

        str_data = weather_basic['cnty'] + ' ' + \
            weather_basic['location']  # 中国 成都

        return str_data
    except Exception as e:
        print(e)
        return None


def weather(msg):
    match = re.match(r'^\/天气 ?(\w*)?', msg['message'])
    if match:
        city = match.group(1)
        str_data = weather_old(city)
        if not str_data:
            str_data = weather_extend(city)
        if not str_data:
            str_data = f"我才不是因为不知道才不告诉你{city}的天气呢"
        send_group_msg(str_data)

# =====Bot=====


def send_group_msg(msg):
    data = {
        "action": "send_group_msg",
        "params": {
            "group_id": 438789224,
            "message": msg
        }
    }
    data = json.dumps(data)
    ws = create_connection("ws://localhost:6700/api/")
    print(f"Sending {data}")
    ws.send(data)
    print("Sent")
    print("Receiving...")
    result = ws.recv()
    print("Received '%s'" % result)
    ws.close()


def on_message(ws, msg):
    print(f"< {msg}")
    msg = json.loads(msg)
    if msg['message_type'] == 'group':
        if msg['group_id'] == 438789224:
            repeat(msg)
            rand(msg)
            bilibili_today(msg)
            weather(msg)


def on_error(ws, error):
    print(error)


def on_close(ws):
    print("### closed ###")


if __name__ == "__main__":
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("ws://localhost:6700/event/",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()
