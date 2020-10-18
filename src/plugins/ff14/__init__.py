""" 最终幻想XIV

各种小工具
"""
from nonebot import CommandGroup
from nonebot.permission import GROUP
from nonebot.typing import Bot, Event

from src.utils.helpers import strtobool

from .gate import get_direction
from .news import news_data

ff14 = CommandGroup('ff14', priority=1, block=True)

#region 藏宝选门
gate = ff14.command('gate')


@gate.args_parser
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    if not stripped_arg:
        await gate.reject('你什么都不输入我怎么知道呢，请告诉我有几个门！')

    if stripped_arg not in ['2', '3']:
        await gate.reject('暂时只支持两个门或者三个门的情况，请重新输入吧。')

    state['door_number'] = int(stripped_arg)


@gate.handle()
async def handle_first_gate(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()
    if stripped_arg in ['2', '3']:
        state['door_number'] = int(stripped_arg)


@gate.got('door_number', prompt='总共有多少个门呢？')
async def handle_gate(bot: Bot, event: Event, state: dict):
    direction = get_direction(state['door_number'])
    await gate.finish(direction)


#endregion
#region 新闻推送
news = ff14.command('news')


@news.args_parser
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    if not stripped_arg:
        await news.reject('你什么都不输入我怎么知道呢，请告诉我有几个门！')

    if stripped_arg not in ['2', '3']:
        await news.reject('暂时只支持两个门或者三个门的情况，请重新输入吧。')

    state['door_number'] = int(stripped_arg)


@news.handle()
async def handle_first_news(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()
    if stripped_arg:
        if strtobool(stripped_arg):
            if not news_data.is_enabled:
                news_data.enable()
            await news.finish('已开始新闻自动推送')
        else:
            if news_data.is_enabled:
                news_data.disable()
            await news.finish('已停止新闻自动推送')
    else:
        if news_data.is_enabled:
            await news.finish('新闻自动推送开启中')
        else:
            await news.finish('新闻自动推送关闭中')


#endregion
