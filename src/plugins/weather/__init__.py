""" 天气插件
"""
from nonebot import on_command
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.params import State
from nonebot.typing import T_State

from .eorzean import eorzean_weather
from .heweather import heweather

weather_cmd = on_command("weather", aliases={"天气"})
weather_cmd.__doc__ = """
天气预报

查询天气
/weather 成都
也支持英文
/weather chengdu
还支持外国
/weather Tokyo
甚至支持最终幻想XIV
/weather 格里达尼亚
如果查询结果不对，还可以指定城市所属行政区划
/weather 西安 黑龙江
"""


@weather_cmd.handle()
async def weather_handle_first_receive(event: MessageEvent, state: T_State = State()):
    argv = str(event.message).strip().split()

    if len(argv) == 1:
        state["location"] = argv[0]
    if len(argv) > 1:
        state["location"] = argv[0]
        state["adm"] = argv[1]


@weather_cmd.got("location", prompt="你想查询哪个城市的天气呢？")
async def weather_handle(event: MessageEvent, state: T_State = State()):
    weather_report = await get_weather_of_location(state["location"], state.get("adm"))
    await weather_cmd.finish(weather_report)


@weather_cmd.args_parser
async def weather_args_parser(event: MessageEvent, state: T_State = State()):
    args = str(event.message).strip()

    if not args:
        await weather_cmd.reject("要查询的城市名称不能为空呢，请重新输入！")

    state[state["_current_key"]] = args


async def get_weather_of_location(location: str, adm: str = None) -> str:
    """根据城市名与城市所属行政区划获取天气数据"""
    # 艾欧泽亚的天气
    str_data = eorzean_weather(location)
    if not str_data:
        str_data = await heweather(location, adm)
    if not str_data:
        str_data = f"我才不是因为不知道才不告诉你{location}的天气呢"
    return str_data
