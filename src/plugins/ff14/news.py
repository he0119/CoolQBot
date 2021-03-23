""" 消息推送 """
from datetime import datetime, timedelta
from typing import Dict, Optional

import httpx
from nonebot import logger, require

from src.utils.helpers import get_first_bot

from .config import plugin_config

scheduler = require("nonebot_plugin_apscheduler").scheduler


class News:
    def __init__(self):
        # 新闻数据的地址
        self._url = 'http://api.act.sdo.com/UnionNews/List?gameCode=ff&category=5309,5310,5311,5312,5313&pageIndex=0&pageSize=5'
        # 定时任务
        self._job = None

        self.init()

    def init(self) -> None:
        """ 初始化新闻自动推送 """
        logger.info('初始化 最终幻想XIV 新闻推送')
        # 启动机器人后先运行一次
        scheduler.add_job(self.push_news,
                          'date',
                          run_date=(datetime.now() + timedelta(seconds=30)))
        self._job = scheduler.add_job(self.push_news,
                                      'interval',
                                      minutes=plugin_config.push_news_interval)

    async def get_news(self) -> Optional[Dict]:
        """ 获取最新的新闻 """
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(self._url)
                if r.status_code != 200:
                    # 如果 HTTP 响应状态码不是 200，说明调用失败
                    return None
                return r.json()
        except (httpx.HTTPError, KeyError) as e:
            logger.error(f'获取新闻出错，{e}')
            # 抛出上面任何异常，说明调用失败
            return None

    @staticmethod
    def format_message(item: Dict) -> str:
        """ 格式化消息 """
        message = ''
        message += f'{item["Title"]}\n'
        message += f'{item["Author"]}\n'
        message += f'{item["Summary"]}'
        return message

    async def push_news(self) -> None:
        """ 推送消息 """
        # 没有启用的群则不推送消息
        if not plugin_config.push_news_group_id:
            return

        logger.info('开始检查 最终幻想XIV 新闻')
        news_list = []

        news = await self.get_news()
        if news is None:
            logger.error('最终幻想XIV 新闻获取失败')
            return

        if not plugin_config.push_news_last_news_id:
            # 如果初次运行，则记录并发送第一条新闻
            plugin_config.push_news_last_news_id = news['Data'][0]['Id']
            news_list.append(news['Data'][0])

        for item in news['Data']:
            if item['Id'] <= plugin_config.push_news_last_news_id:
                break
            news_list.append(item)

        if news_list:
            # 参考 [Yobot](https://github.com/pcrbot/yobot/blob/master/src/client/ybplugins/push_news.py) 的格式
            msg = '最终幻想XIV官网更新：\n=======\n' + '\n-------\n'.join(
                map(self.format_message, news_list))
            for group_id in plugin_config.push_news_group_id:
                await get_first_bot().send_msg(message_type='group',
                                               group_id=group_id,
                                               message=msg)
            # 添加最新的那一条新闻的 ID
            plugin_config.push_news_last_news_id = news_list[0]['Id']


news = News()
