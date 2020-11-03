""" 天气插件
"""
from typing import Optional

from jieba import posseg
from nonebot import on_command
from nonebot.typing import Bot, Event

from .eorzean import eorzean_weather
from .heweather import heweather

weather_cmd = on_command('weather', aliases={'天气'}, block=True)
weather_cmd.__doc__ = """
weather 天气

天气预报

查询天气
/weather 成都
也支持英文
/weather chengdu
还支持外国
/weather Tokyo
甚至支持最终幻想XIV
/weather 格里达尼亚
"""


@weather_cmd.handle()
async def _(bot: Bot, event: Event, state: dict):
    args = str(event.message).strip()

    if args:
        state['city'] = args


@weather_cmd.got('city', prompt='你想查询哪个城市的天气呢？')
async def _(bot: Bot, event: Event, state: dict):
    weather_report = await get_weather_of_city(state['city'])
    await weather_cmd.finish(weather_report)


@weather_cmd.args_parser
async def _(bot: Bot, event: Event, state: dict):
    args = str(event.message).strip()

    if not args:
        weather_cmd.reject('要查询的城市名称不能为空呢，请重新输入！')

    state[state['_current_key']] = args


async def get_weather_of_city(city: str) -> str:
    """ 根据城市名获取天气数据 """
    # 艾欧泽亚的天气
    str_data = eorzean_weather(city)
    if not str_data:
        str_data = await heweather(city)
    if not str_data:
        str_data = f'我才不是因为不知道才不告诉你{city}的天气呢'
    return str_data


def get_city(msg: str) -> Optional[str]:
    """ 提取消息中的地名 """
    # 对消息进行分词和词性标注
    words = posseg.lcut(msg)
    # 遍历 posseg.lcut 返回的列表
    for word in words:
        # 每个元素是一个 pair 对象，包含 word 和 flag 两个属性，分别表示词和词性
        if word.flag == 'ns':
            # ns 词性表示地名
            return word.word

    return None
