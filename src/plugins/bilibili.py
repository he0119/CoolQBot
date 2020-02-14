""" 获取B站番剧的今日更新

https://www.bilibili.com/anime/timeline
"""
import re

import httpx
from nonebot import CommandSession, on_command


@on_command('bilibili', only_to_me=False)
async def bilibili_today(session: CommandSession):
    try:
        output = ''
        async with httpx.AsyncClient() as client:
            response = await client.get('https://bangumi.bilibili.com/web_api/timeline_global')
            rjson = response.json()
            for day in rjson['result']:
                if (day['is_today'] == 1):
                    for item in day['seasons']:
                        output += f'{item["pub_time"]} : {item["title"]}\n'

            # 去掉最后一个\n
            await session.send(output[:-1])
    except:
        await session.send('获取番剧信息失败了~>_<~')
