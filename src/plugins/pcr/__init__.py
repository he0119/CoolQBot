""" 公主连结Re:Dive

日程推送和查询

参考 https://github.com/pcrbot/yobot
"""
from nonebot import on_command
from nonebot.plugin import PluginMetadata

from .data import calendar

__plugin_meta__ = PluginMetadata(
    name="公主连结Re:Dive",
    description="日程表查询",
    usage="获取一周日程表\n/公主连结日程表",
)

# region 日程表
calendar_cmd = on_command("公主连结日程表")


@calendar_cmd.handle()
async def calendar_handle():
    await calendar_cmd.finish(await calendar.get_week_events())


# endregion
