""" 公主连结Re:Dive

B站动态推送
日程推送和查询

参考 https://github.com/pcrbot/yobot
"""
from nonebot import CommandGroup
from nonebot.typing import Bot, Event

from src.utils.helpers import strtobool

from .config import config
from .news import news_data
from .calender import calender_data

pcr = CommandGroup('pcr', priority=1, block=True)

#region 新闻推送
news = pcr.command('news')


@news.handle()
async def handle_first_news(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()
    if stripped_arg:
        if strtobool(stripped_arg):
            if not news_data.is_enabled:
                news_data.enable()
            await news.finish('已开始动态自动推送')
        else:
            if news_data.is_enabled:
                news_data.disable()
            await news.finish('已停止动态自动推送')
    else:
        if news_data.is_enabled:
            await news.finish('动态自动推送开启中')
        else:
            await news.finish('动态自动推送关闭中')


#endregion
#region 日程表
calender = pcr.command('calender', aliases={('pcr', '日程表'), ('pcr', '日程')})


@calender.handle()
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    if stripped_arg in ['status', '状态']:
        if calender_data.is_enabled:
            await calender.finish('日程自动推送开启中')
        else:
            await calender.finish('日程自动推送关闭中')
    elif stripped_arg:
        if strtobool(stripped_arg):
            if not calender_data.is_enabled:
                calender_data.enable()
            await calender.finish('已开始日程自动推送')
        else:
            if calender_data.is_enabled:
                calender_data.disable()
            await calender.finish('已停止日程自动推送')
    else:
        await calender.finish(await calender_data.get_week_events())


#endregion
