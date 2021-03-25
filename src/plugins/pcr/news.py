""" B站动态推送

https://space.bilibili.com/353840826/dynamic
"""
import json
from datetime import datetime, timedelta
from typing import Dict

import httpx
from nonebot import logger, require

from src.utils.helpers import get_first_bot

from .config import plugin_config

scheduler = require("nonebot_plugin_apscheduler").scheduler


class News:
    def __init__(self):
        # 动态的地址
        self._url = 'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history?host_uid=353840826'
        # 定时任务
        self._job = None

        self.init()

    def init(self):
        """ 初始化动态自动推送 """
        logger.info('初始化 公主连结Re:Dive 动态推送')
        # 启动之后先运行一次
        scheduler.add_job(self.push_news,
                          'date',
                          run_date=(datetime.now() + timedelta(seconds=30)))
        self._job = scheduler.add_job(self.push_news,
                                      'interval',
                                      minutes=plugin_config.push_news_interval)

    async def get_news(self):
        """ 获取最新的动态 """
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(self._url)
                if r.status_code != 200:
                    # 如果 HTTP 响应状态码不是 200，说明调用失败
                    return None
                cards = r.json()['data']['cards']
                return list(
                    map(
                        lambda x: {
                            'desc': x['desc'],
                            'card': json.loads(x['card']),
                        }, cards))
        except (httpx.HTTPError, KeyError) as e:
            logger.error(f'获取动态出错，{e}')
            # 抛出上面任何异常，说明调用失败
            return None

    @staticmethod
    def get_news_id(news: Dict) -> int:
        """ 获取新闻的 ID """
        return news['desc']['dynamic_id']

    @staticmethod
    def format_message(item):
        """ 格式化消息 """
        if 'item' in item['card']:
            card_item = item['card']['item']
        else:
            card_item = item['card']
        card_desc = item['desc']

        message = ''

        # 只需要其中一个有内容就好
        if 'title' in card_item and card_item['title']:
            message += card_item['title']
        elif 'desc' in card_item and card_item['desc']:
            message += card_item['desc']
        elif 'description' in card_item and card_item['description']:
            message += card_item['description']
        elif 'content' in card_item and card_item['content']:
            message += card_item['content']
        elif 'summary' in card_item and card_item['summary']:
            message += card_item['summary']

        message += f'https://t.bilibili.com/{card_desc["dynamic_id"]}'

        return message

    async def push_news(self):
        """ 推送消息 """
        # 没有启用的群则不推送消息
        if not plugin_config.push_news_group_id:
            return

        logger.info('开始检查 公主连结Re:Dive 动态')
        news_list = []

        news = await self.get_news()
        if news is None:
            logger.error('公主连结Re:Dive 动态获取失败')
            return

        if not plugin_config.push_news_last_news_id:
            # 如果初次运行，则记录并发送第一条动态
            plugin_config.push_news_last_news_id = self.get_news_id(news[0])
            news_list.append(news[0])

        for item in news:
            if self.get_news_id(item) <= plugin_config.push_news_last_news_id:
                break
            news_list.append(item)

        if news_list:
            # 参考 [Yobot](https://github.com/pcrbot/yobot/blob/master/src/client/ybplugins/push_news.py) 的格式
            msg = '公主连结Re:Dive B站动态更新：\n=======\n' + '\n-------\n'.join(
                map(self.format_message, news_list))
            for group_id in plugin_config.push_news_group_id:
                await get_first_bot().send_msg(message_type='group',
                                               group_id=group_id,
                                               message=msg)
            # 添加最新的那一条动态的 ID
            plugin_config.push_news_last_news_id = self.get_news_id(
                news_list[0])


news_obj = News()
