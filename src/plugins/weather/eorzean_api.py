""" 艾欧泽亚天气预报
"""
import time

from EorzeaEnv import EorzeaLang, EorzeaPlaceName, EorzeaTime, EorzeaWeather


def eorzean_weather(location: str) -> str | None:
    """艾欧泽亚天气

    利姆萨·罗敏萨
    当前天气：碧空
    还剩12分55秒切换到天气：阴云
    """
    try:
        now = time.time()
        place_name = EorzeaPlaceName(location, strict=False)

        weathers: list[str] = []
        for t in EorzeaTime.weather_period(10, now):
            weathers.append(
                EorzeaWeather.forecast(
                    place_name, t, lang=EorzeaLang.ZH_SC, strict=True
                )
            )
        str_data = f"{place_name.value}\n当前天气：{weathers[0]}"
        for num, weather in enumerate(weathers[1:]):
            str_data += f"\n还剩{next_weather_time(int(now), num)}切换到天气：{weather}"
        return str_data
    except Exception as e:
        return None


def next_weather_time(date: int, count: int) -> str:
    """计算下一个天气时段所剩时间(格式mm:ss)"""
    # 计算当前时间戳所属的区间(以4200s为一个完整的周期，艾欧泽亚日)
    increament = (date + 1400 - (date % 1400)) % 4200
    cur_time = date % 4200
    if increament > cur_time:
        left_sec = increament - cur_time
    else:
        left_sec = 4200 - cur_time
    left_sec += 1400 * count

    hour = left_sec // 3600
    minute = (left_sec // 60) % 60
    second = left_sec % 60

    if hour:
        return f"{hour}时{minute}分{second}秒"
    return f"{minute}分{second}秒"
