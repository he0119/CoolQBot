""" 艾欧泽亚天气预报
"""
import time

from .eorzean_data import locationIndex, weatherIndex, weatherRateIndex


def int_overflow(n: int):
    """ 模拟 JavaScript 的溢出
    """
    return n & (2**32 - 1)


def unsigned_right_shitf(n: int, i: int):
    """ 模拟 JavaScript 的无符号右移
    """
    return (n & (2**32 - 1)) >> i


def forecastTarget(date: int):
    """ 预测
    """
    bell = date // 175
    increment = (bell + 8 - (bell % 8)) % 24

    totalDays = date // 4200

    calcBase = totalDays * 100 + increment

    step1 = int_overflow((calcBase << 11) ^ calcBase)
    step1 = unsigned_right_shitf(step1, 0)
    step2 = (unsigned_right_shitf(step1, 8) ^ step1)
    step2 = unsigned_right_shitf(step2, 0)

    return step2 % 100


def calc_eorzean_weather(date: int, location: str):
    """ 计算艾欧泽亚天气
    """
    for index in locationIndex:
        if locationIndex[index]['name'] == location:
            weatherRate = weatherRateIndex[str(
                locationIndex[index]['weatherRate']
            )]
            break

    target = forecastTarget(date)

    for rate in weatherRate['rates']:
        if target < rate['rate']:
            weather = weatherIndex[rate['weather']]
            return weather


def eorzean_weather(location: str):
    """ 艾欧泽亚天气

    利姆萨·罗敏萨
    当前天气：碧空
    还剩12分55秒切换到天气：阴云
    """
    try:
        str_data = f'{location}\n'

        date = int(time.time())
        weather = calc_eorzean_weather(date, location)
        furWeather = calc_eorzean_weather(date + 1400, location)
        str_data += f'当前天气：{weather}\n'
        str_data += f'还剩{next_weather_time(date)}切换到天气：{furWeather}'

        return str_data
    except:
        return None


def next_weather_time(date: int):
    """ 计算下一个天气时段所剩时间(格式mm:ss)
    """
    # 计算当前时间戳所属的区间(以4200s为一个完整的周期，艾欧泽亚日)
    increament = (date + 1400 - (date % 1400)) % 4200
    cur_time = date % 4200
    if increament > cur_time:
        left_sec = increament - cur_time
    else:
        left_sec = 4200 - cur_time
    minute = left_sec // 60
    second = left_sec % 60

    return f'{minute}分{second}秒'
