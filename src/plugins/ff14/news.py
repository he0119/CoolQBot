from datetime import datetime, timedelta

import feedparser
import httpx

from coolqbot import PluginData, bot


class News:
    def __init__(self):
        self._data = PluginData('ff14', config=True)
        self._rss_url = 'http://rsshub:1200/ff14/ff14_zh/news'
        self._last_id = None
        # 定时任务
        self._job = None
        # 当前状态
        self._status = None

        # 根据配置启动
        if bool(int(self._data.get_config('ff14', 'push_news', '0'))):
            self.enable()

    def enable(self):
        bot.logger.info('初始化 最终幻想XIV RSS 订阅')
        # 开启后先运行一次
        bot.scheduler.add_job(
            self.send_news,
            'date',
            run_date=(datetime.now() + timedelta(seconds=30))
        )
        self._job = bot.scheduler.add_job(
            self.send_news, 'interval', minutes=self.interval
        )
        self._data.set_config('ff14', 'push_news', '1')

    def disable(self):
        self._job.remove()
        self._data.set_config('ff14', 'push_news', '0')

    @property
    def is_enabled(self):
        """ 是否启用服务器状态监控 """
        if self._job:
            return True
        else:
            return False

    @property
    def interval(self):
        return int(self._data.get_config('ff14', 'push_news_interval', '30'))

    @property
    def last_id(self):
        return self._data.get_config('ff14', 'push_news_last_id')

    @last_id.setter
    def last_id(self, last_id):
        self._data.set_config('ff14', 'push_news_last_id', last_id)

    async def get_news_feed(self):
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(self._rss_url)
                if r.status_code != 200:
                    # 如果 HTTP 响应状态码不是 200，说明调用失败
                    return None
                feed = feedparser.parse(r.text)
                if feed['bozo']:
                    bot.logger.error('RSS 解析错误，无法获得最终幻想XIV的新闻')
                    return None
                return feed
        except (httpx.HTTPError, KeyError) as e:
            bot.logger.warn(f'获取 RSS 出错，{e}')
            # 抛出上面任何异常，说明调用失败
            return None

    def format_message(self, item):
        message = ''
        message += f'{item["title"]}\n'
        message += item['link']
        return message

    async def send_news(self):
        bot.logger.info('开始检查 最终幻想XIV 新闻')
        news_list = []

        feed = await self.get_news_feed()
        if feed is None:
            bot.logger.warn('最终幻想XIV RSS 订阅获取失败')
            return

        if not self.last_id:
            # 如果初次运行，则记录并发送第一条新闻
            self.last_id = feed['entries'][0]['id']
            news_list.append(feed['entries'][0])

        for item in feed['entries']:
            if item['id'] == self.last_id:
                break
            news_list.append(item)

        if news_list:
            group_id = bot.get_bot().config.GROUP_ID[0]
            for item in news_list:
                await bot.get_bot().send_msg(
                    message_type='group',
                    group_id=group_id,
                    message=self.format_message(item)
                )
                self.last_id = item['id']


news = News()
