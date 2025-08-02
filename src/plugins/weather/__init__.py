"""天气插件"""

from nonebot import require
from nonebot.adapters import Bot, Event
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.typing import T_State

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, MultiVar, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension

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
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)

weather_cmd = on_alconna(
    Alconna(
        "weather",
        Args["location?#位置", MultiVar(str, flag="+")],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"天气"},
    use_cmd_start=True,
    block=True,
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "天气"}),
    ],
)


async def parse_location(event: Event, bot: Bot, state: T_State, location: str, **kwargs) -> tuple[str, ...] | None:
    return tuple(location.strip().split()) if location else None


@weather_cmd.handle()
async def weather_handle_first_receive(location: Match[tuple[str, ...]]):
    if location.available:
        weather_cmd.set_path_arg("location", location.result)


@weather_cmd.got_path("location", prompt="你想查询哪个城市的天气呢？", middleware=parse_location)
async def weather_handle(location: tuple[str, ...]):
    """查询天气"""
    weather_report = await get_weather_of_location(*location[:2])
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
