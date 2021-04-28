""" 公主连结Re:Dive

B站动态推送
日程推送和查询

参考 https://github.com/pcrbot/yobot
"""
from nonebot import CommandGroup
from nonebot.adapters import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.typing import T_State

from src.utils.helpers import strtobool

from .calender import calender_obj
from .config import plugin_config
from .news import news_obj

pcr = CommandGroup('pcr', block=True)

#region 新闻推送
news_cmd = pcr.command('news')
news_cmd.__doc__ = """
pcr.news

公主连结Re:Dive 新闻推送

当前新闻推送状态
/pcr.news
开启推送
/pcr.news on
关闭推送
/pcr.news off
"""


@news_cmd.handle()
async def news_handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.message).strip()

    group_id = event.group_id

    if args and group_id:
        if strtobool(args):
            plugin_config.push_news_group_id += [group_id]
            await news_cmd.finish('已开始新闻自动推送')
        else:
            plugin_config.push_news_group_id = [
                n for n in plugin_config.push_news_group_id if n != group_id
            ]
            await news_cmd.finish('已停止新闻自动推送')
    else:
        if group_id in plugin_config.push_news_group_id:
            await news_cmd.finish('新闻自动推送开启中')
        else:
            await news_cmd.finish('新闻自动推送关闭中')


#endregion
#region 日程表
calender_cmd = pcr.command('calender', aliases={('pcr', '日程表'), ('pcr', '日程')})
calender_cmd.__doc__ = """
pcr.calender pcr.日程表 pcr.日程

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
async def calender_handle(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.message).strip()

    group_id = event.group_id

    if args in ['status', '状态']:
        if group_id in plugin_config.push_calender_group_id:
            await news_cmd.finish('日程自动推送开启中')
        else:
            await news_cmd.finish('日程自动推送关闭中')
    elif args and group_id:
        if strtobool(args):
            plugin_config.push_calender_group_id += [group_id]
            await news_cmd.finish('已开始日程自动推送')
        else:
            plugin_config.push_calender_group_id = [
                n for n in plugin_config.push_calender_group_id
                if n != group_id
            ]
            await news_cmd.finish('已停止日程自动推送')
    else:
        await calender_cmd.finish(await calender_obj.get_week_events())


#endregion
