""" 消息推送 """
from datetime import datetime, timedelta

import httpx
from nonebot import get_driver, logger, scheduler

from src.utils.helpers import get_first_bot

from .config import config


class News:
    def __init__(self):
        # 新闻数据的地址
        self._url = 'http://api.act.sdo.com/UnionNews/List?gameCode=ff&category=5309,5310,5311,5312,5313&pageIndex=0&pageSize=5'
        # 定时任务
        self._job = None

        # 根据配置启动
        if config.push_news:
            self.enable()

    def enable(self):
        """ 开启新闻自动推送 """
        logger.info('初始化 最终幻想XIV 新闻推送')
        # 开启后先运行一次
        scheduler.add_job(
            self.push_news,
            'date',
            run_date=(datetime.now() + timedelta(seconds=30))
        )
        self._job = scheduler.add_job(
            self.push_news, 'interval', minutes=config.push_news_interval
        )
        config.push_news = True

    def disable(self):
        """ 关闭新闻自动推送 """
        self._job.remove()
        self._job = None
        config.push_news = False

    @property
    def is_enabled(self):
        """ 是否启用新闻自动推送 """
        if self._job:
            return True
        else:
            return False

    async def get_news(self):
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

    def format_message(self, item):
        """ 格式化消息 """
        message = ''
        message += f'{item["Title"]}\n'
        message += f'{item["Author"]}\n'
        message += f'{item["Summary"]}'
        return message

    async def push_news(self):
        """ 推送消息 """
        logger.info('开始检查 最终幻想XIV 新闻')
        news_list = []

        news = await self.get_news()
        if news is None:
            logger.error('最终幻想XIV 新闻获取失败')
            return

        if not config.push_news_last_news_id:
            # 如果初次运行，则记录并发送第一条新闻
            config.push_news_last_news_id = news['Data'][0]['Id']
            news_list.append(news['Data'][0])

        for item in news['Data']:
            if item['Id'] <= config.push_news_last_news_id:
                break
            news_list.append(item)

        if news_list:
            # 参考 [Yobot](https://github.com/pcrbot/yobot/blob/master/src/client/ybplugins/push_news.py) 的格式
            msg = '最终幻想XIV官网更新：\n=======\n' + '\n-------\n'.join(
                map(self.format_message, news_list)
            )
            for group_id in get_driver().config.group_id:
                await get_first_bot().send_msg(
                    message_type='group', group_id=group_id, message=msg
                )
            # 添加最新的那一条新闻的 ID
            config.push_news_last_news_id = news_list[0]['Id']


news_data = News()
