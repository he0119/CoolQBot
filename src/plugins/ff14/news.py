import json
from datetime import datetime, timedelta

import httpx
from nonebot import get_bot, logger, scheduler

from coolqbot import PluginData


class News:
    def __init__(self):
        self._data = PluginData('ff14', config=True)
        # 新闻数据的地址
        self._url = 'http://api.act.sdo.com/UnionNews/List?gameCode=ma&category=5309,5310,5311,5312,5313&pageIndex=0&pageSize=5'
        # 定时任务
        self._job = None

        # 根据配置启动
        if bool(int(self._data.get_config('ff14', 'push_news', '0'))):
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
            self.push_news, 'interval', minutes=self.interval
        )
        self._data.set_config('ff14', 'push_news', '1')

    def disable(self):
        """ 关闭新闻自动推送 """
        self._job.remove()
        self._data.set_config('ff14', 'push_news', '0')

    @property
    def is_enabled(self):
        """ 是否启用新闻自动推送 """
        if self._job:
            return True
        else:
            return False

    @property
    def interval(self):
        """ 自动推送新闻的间隔，单位 分钟 """
        return int(self._data.get_config('ff14', 'push_news_interval', '30'))

    @property
    def last_news_date(self):
        """ 上次推送新闻的发布日期 """
        return self._data.get_config('ff14', 'push_news_last_news_date')

    @last_news_date.setter
    def last_news_date(self, date_str: str):
        self._data.set_config('ff14', 'push_news_last_news_date', date_str)

    async def get_news(self):
        """ 获取最新的新闻 """
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(self._url)
                if r.status_code != 200:
                    # 如果 HTTP 响应状态码不是 200，说明调用失败
                    return None
                return json.loads(r.text)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
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

        if not self.last_news_date:
            # 如果初次运行，则记录并发送第一条新闻
            self.last_news_date = news['Data'][0]['PublishDate']
            news_list.append(news['Data'][0])

        for item in news['Data']:
            if item['PublishDate'] == self.last_news_date:
                break
            news_list.append(item)

        if news_list:
            group_id = get_bot().config.GROUP_ID[0]
            for item in news_list:
                await get_bot().send_msg(
                    message_type='group',
                    group_id=group_id,
                    message=self.format_message(item)
                )
                self.last_news_date = item['PublishDate']


news = News()
