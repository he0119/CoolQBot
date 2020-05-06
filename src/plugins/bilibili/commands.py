#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author         : richardchien
@Date           : 2020-04-14 22:10:53
@LastEditors    : yanyongyu
@LastEditTime   : 2020-04-14 22:21:30
@Description    : None
@GitHub         : https://github.com/richardchien
"""
__author__ = "richardchien"

import re
import math
from datetime import datetime
from collections import defaultdict
from datetime import datetime, timedelta

from nonebot import CommandSession

from . import cg, __plugin_usage__
from .data_source import get_anime_list, get_timeline_list

WEB_URL = 'https://www.bilibili.com/anime/index/#' + \
          'season_version=-1&area=-1&is_finish=-1&' + \
          'copyright=-1&season_status=-1&' + \
          'season_month={month}&pub_date={year}' + \
          '&style_id=-1&order=3&st=1&sort=0&page=1'


@cg.command('index', aliases={'番剧索引', '番剧', '新番'})
async def index(session: CommandSession):
    now = datetime.now()
    year = session.state.get('year', now.year)
    month = session.state.get('month', now.month)
    month = math.ceil(month / 3) * 3 - 3 + 1

    anime_list = await get_anime_list(year, month)
    if not anime_list:
        session.finish('没有查询到相关番剧……')

    reply = f'{year}年{month}月番剧\n按追番人数排序，前20部如下：\n\n'
    for anime in anime_list:
        title = anime.get('title')
        index_show = anime.get('index_show', '不详')
        if not title:
            continue
        reply += f'{title}  {index_show}\n'

    web_url = WEB_URL.format(year=year, month=month)
    reply += f'\n更多详细资料见哔哩哔哩官网 {web_url}'
    session.finish(reply)


@index.args_parser
async def _(session: CommandSession):
    argv = session.current_arg_text.split()

    year = None
    month = None
    if len(argv) == 2 and \
            re.fullmatch(r'(?:20)?\d{2}', argv[0]) and \
            re.fullmatch(r'\d{1,2}', argv[1]):
        year = int(argv[0]) if len(argv[0]) > 2 else 2000 + int(argv[0])
        month = int(argv[1])
    elif len(argv) == 1 and re.fullmatch(r'\d{1,2}', argv[0]):
        month = int(argv[0])
    elif len(argv) == 1 and re.fullmatch(r'(?:20)?\d{2}-\d{1,2}', argv[0]):
        year, month = [int(x) for x in argv[0].split('-')]
        year = 2000 + year if year < 100 else year
    elif len(argv):
        await session.send('抱歉无法识别输入的参数，下面将给出本季度的番剧～')

    if year is not None:
        session.state['year'] = year
    if month is not None:
        session.state['month'] = month


@cg.command('timeline', aliases={'番剧时间表', '新番时间表'})
async def timeline(session: CommandSession):
    timeline_list = await get_timeline_list()
    if timeline_list is None:
        session.finish('查询失败了……')

    date = session.state.get('date')
    name = session.state.get('name')

    if date:
        timeline_list = list(
            filter(lambda x: x.get('pub_date', '').endswith(date),
                   timeline_list))
    if name:
        name = name.strip()
        timeline_list = list(
            filter(lambda x: name.lower() in x.get('title', '').lower(),
                   timeline_list))
        if len(set(map(lambda x: x['title'], timeline_list))) > 1:
            timeline_list = list(
                filter(lambda x: len(name) > len(x['title']) / 4,
                       timeline_list))

    if date and name:
        if not timeline_list:
            reply = '没更新'
        else:
            reply = '\n'.join(
                ('更新了' if item['is_published'] else f'将在{item["ontime"]}更新') +
                (f'第{item["ep_index"]}话' if item['ep_index'].isdigit(
                ) else item['ep_index']) for item in timeline_list)
        session.finish(reply)

    if not timeline_list:
        session.finish('没有找到符合条件的时间表……')

    if date:
        month, day = [int(x) for x in date.split('-')]
        reply = f'在{month}月{day}日更新的番剧有：\n\n'
        reply += '\n'.join(f'{item["title"] or "未知动画"}  '
                           f'{item["ontime"] or "未知时间"}  ' +
                           (f'第{item["ep_index"]}话' if item['ep_index'].isdigit(
                           ) else item['ep_index']) for item in timeline_list)
        session.finish(reply)

    if name:
        anime_dict = defaultdict(list)
        for item in timeline_list:
            anime_dict[item['title']].append(item)

        for name, items in anime_dict.items():
            reply = f'{name}\n'
            for item in items:
                _, month, day = [int(x) for x in item['pub_date'].split('-')]
                reply += '\n' + ('已' if item['is_published'] else '将') + \
                         f'在{month}月{day}日{item["ontime"]}更新' + \
                         (f'第{item["ep_index"]}话'
                          if item['ep_index'].isdigit()
                          else item['ep_index'])
            await session.send(reply)


@timeline.args_parser
async def _(session: CommandSession):
    if session.state:
        return

    m = re.search(r'(?:(-?\d{1,2})(?:-(\d{1,2}))?)?\s*(.+)?',
                  session.current_arg_text.strip())
    if not m:
        session.finish(__plugin_usage__("description"))

    num1 = m.group(1)
    num2 = m.group(2)
    name = m.group(3)

    if num1 is None and name is None:
        session.finish(__plugin_usage__("description"))

    if num1 is not None and num2 is not None:
        date = f'%02d-%02d' % (int(num1), int(num2))
    elif num1 is not None:
        date = (datetime.now() + timedelta(days=int(num1))).strftime('%m-%d')
    else:
        date = None

    session.state['date'] = date
    session.state['name'] = name
