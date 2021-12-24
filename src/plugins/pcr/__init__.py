""" 公主连结Re:Dive

日程推送和查询

参考 https://github.com/pcrbot/yobot
"""
from nonebot import CommandGroup
from nonebot.adapters.onebot.v11.event import GroupMessageEvent

from src.utils.helpers import strtobool

from .calender import calender_obj
from .config import plugin_config

pcr = CommandGroup("pcr")

# region 日程表
calender_cmd = pcr.command("calender", aliases={("pcr", "日程表"), ("pcr", "日程")})
calender_cmd.__doc__ = """
公主连结Re:Dive 日程表

获取一周日程表
/pcr.calender
当前日程推送状态
/pcr.calender status
开启日程自动推送
/pcr.calender on
关闭日程自动推送
/pcr.calender off
"""


@calender_cmd.handle()
async def calender_handle(event: GroupMessageEvent):
    args = str(event.message).strip()

    group_id = event.group_id

    if args in ["status", "状态"]:
        if group_id in plugin_config.push_calender_group_id:
            await calender_cmd.finish("日程自动推送开启中")
        else:
            await calender_cmd.finish("日程自动推送关闭中")
    elif args and group_id:
        if strtobool(args):
            plugin_config.push_calender_group_id += [group_id]
            await calender_cmd.finish("已开始日程自动推送")
        else:
            plugin_config.push_calender_group_id = [
                n for n in plugin_config.push_calender_group_id if n != group_id
            ]
            await calender_cmd.finish("已停止日程自动推送")
    else:
        await calender_cmd.finish(await calender_obj.get_week_events())


# endregion
