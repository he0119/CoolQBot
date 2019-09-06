""" 天气插件
"""
from jieba import posseg
from nonebot import (
    CommandSession, IntentCommand, NLPSession, on_command, on_natural_language
)

from .eorzean import eorzean_weather
from .heweather import heweather


@on_command('weather', aliases=('天气', '天气预报', '查天气'), only_to_me=False)
async def weather(session: CommandSession):
    city = session.get('city', prompt='你想查询哪个城市的天气呢？')
    weather_report = await get_weather_of_city(city)
    await session.send(weather_report)


@weather.args_parser
async def _(session: CommandSession):
    stripped_arg = session.current_arg_text.strip()

    if session.is_first_run:
        if stripped_arg:
            session.state['city'] = stripped_arg
        return

    if not stripped_arg:
        session.pause('要查询的城市名称不能为空呢，请重新输入！')

    session.state[session.current_key] = stripped_arg


# on_natural_language 装饰器将函数声明为一个自然语言处理器
# keywords 表示需要响应的关键词，类型为任意可迭代对象，元素类型为 str
# 如果不传入 keywords，则响应所有没有被当作命令处理的消息
@on_natural_language(keywords={'天气'})
async def _(session: NLPSession):
    # 去掉消息首尾的空白符
    stripped_msg = session.msg_text.strip()

    city = get_city(stripped_msg)

    # 返回意图命令，前两个参数必填，分别表示置信度和意图命令名
    return IntentCommand(90.0, 'weather', current_arg=city or '')


async def get_weather_of_city(city):
    """ 根据城市名获取天气数据
    """
    # 艾欧泽亚的天气
    str_data = eorzean_weather(city)
    if not str_data:
        str_data = heweather(city)
    if not str_data:
        str_data = f'我才不是因为不知道才不告诉你{city}的天气呢'
    return str_data


def get_city(msg):
    """ 提取消息中的地名
    """
    # 对消息进行分词和词性标注
    words = posseg.lcut(msg)
    # 遍历 posseg.lcut 返回的列表
    for word in words:
        # 每个元素是一个 pair 对象，包含 word 和 flag 两个属性，分别表示词和词性
        if word.flag == 'ns':
            # ns 词性表示地名
            return word.word

    return None
