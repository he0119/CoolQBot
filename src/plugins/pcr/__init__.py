""" 公主连结Re:Dive

B站动态推送
日程推送和查询

参考 https://github.com/pcrbot/yobot
"""
from nonebot import CommandGroup
from nonebot.typing import Bot, Event

from src.utils.helpers import strtobool

from .calender import calender
from .news import news

pcr = CommandGroup('pcr', priority=1, block=True)

#region 新闻推送
news_cmd = pcr.command('news')
news_cmd.__doc__ = """
pcr.news

公主连结Re:Dive 新闻推送

开启推送
/pcr.news on
关闭推送
/pcr.news off
在本群启用
/pcr.news enable
在本群禁用
/pcr.news disable
"""


@news_cmd.handle()
async def handle_first_news(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()
    if stripped_arg:
        if strtobool(stripped_arg):
            if not news.is_enabled:
                news.enable()
            await news_cmd.finish('已开始动态自动推送')
        else:
            if news.is_enabled:
                news.disable()
            await news_cmd.finish('已停止动态自动推送')
    else:
        if news.is_enabled:
            await news_cmd.finish('动态自动推送开启中')
        else:
            await news_cmd.finish('动态自动推送关闭中')


#endregion
#region 日程表
calender_cmd = pcr.command('calender', aliases={('pcr', '日程表'), ('pcr', '日程')})
calender_cmd.__doc__ = """
pcr.calender pcr.日程表 pcr.日程

公主连结Re:Dive 日程表

获取一周日程表
/pcr.calender
开启日程自动推送
/pcr.calender on
关闭日程自动推送
/pcr.calender off
在本群启用
/pcr.calender enable
在本群禁用
/pcr.calender disable
"""


@calender_cmd.handle()
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    if stripped_arg in ['status', '状态']:
        if calender.is_enabled:
            await calender_cmd.finish('日程自动推送开启中')
        else:
            await calender_cmd.finish('日程自动推送关闭中')
    elif stripped_arg:
        if strtobool(stripped_arg):
            if not calender.is_enabled:
                calender.enable()
            await calender_cmd.finish('已开始日程自动推送')
        else:
            if calender.is_enabled:
                calender.disable()
            await calender_cmd.finish('已停止日程自动推送')
    else:
        await calender_cmd.finish(await calender.get_week_events())


#endregion
