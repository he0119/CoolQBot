'''获取B站番剧的今日更新'''
import json
import re

import requests

from coolqbot.bot import bot


@bot.on_message('group', 'private')
async def bilibili_today(context):
    match = re.match(r'^\/bilibili', context['message'])
    if match:
        try:
            output = ''
            response = requests.get(
                "https://bangumi.bilibili.com/web_api/timeline_global")
            data = response.content.decode('utf-8')
            rjson = json.loads(data)
            for day in rjson['result']:
                if(day['is_today'] == 1):
                    for item in day['seasons']:
                        output += item['pub_time'] + " : " + item['title'] + "\n"
            return {'reply': output, 'at_sender': False}
        except:
            return {'reply': "获取番剧信息失败了~>_<~", 'at_sender': False}
