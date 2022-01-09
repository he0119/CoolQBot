""" 公主连结Re:Dive

日程推送和查询

参考 https://github.com/pcrbot/yobot
"""
from nonebot import CommandGroup

from .data import calendar

pcr = CommandGroup("pcr")

# region 日程表
calendar_cmd = pcr.command("calendar", aliases={("pcr", "日程表"), ("pcr", "日程")})
calendar_cmd.__doc__ = """
公主连结Re:Dive 日程表

获取一周日程表
/pcr.calendar
"""


@calendar_cmd.handle()
async def calendar_handle():
    await calendar_cmd.finish(await calendar.get_week_events())


# endregion
