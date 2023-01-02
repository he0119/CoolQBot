""" 天气插件
"""
from nonebot import on_command
from nonebot.adapters import Message
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg
from nonebot.plugin import PluginMetadata

from .eorzean_api import eorzean_weather
from .heweather_api import heweather

__plugin_meta__ = PluginMetadata(
    name="天气",
    description="查询天气预报（包括艾欧泽亚）",
    usage="""查询天气
/weather 成都
也支持英文
/weather chengdu
还支持外国
/weather Tokyo
甚至支持最终幻想XIV
/weather 格里达尼亚
如果查询结果不对，还可以指定城市所属行政区划
/weather 西安 黑龙江""",
)

weather_cmd = on_command("weather", aliases={"天气"})


@weather_cmd.handle()
async def weather_handle_first_receive(matcher: Matcher, arg: Message = CommandArg()):
    plain_text = arg.extract_plain_text()

    if plain_text:
        matcher.set_arg("location", arg)


@weather_cmd.got("location", prompt="你想查询哪个城市的天气呢？")
async def weather_handle(location: str = ArgPlainText()):
    """查询天气"""
    if not location:
        await weather_cmd.reject("要查询的城市名称不能为空呢，请重新输入！")

    weather_report = await get_weather_of_location(*location.split()[:2])
    await weather_cmd.finish(weather_report)


async def get_weather_of_location(location: str, adm: str | None = None) -> str:
    """根据城市名与城市所属行政区划获取天气数据"""
    # 艾欧泽亚的天气
    str_data = eorzean_weather(location)
    if not str_data:
        str_data = await heweather(location, adm)
    if not str_data:
        str_data = f"我才不是因为不知道才不告诉你{location}的天气呢"
    return str_data
