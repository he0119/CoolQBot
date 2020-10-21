""" 日程表

https://tools.yobot.win/calender/#cn
"""
from datetime import datetime, timedelta
from typing import Dict

import httpx
from nonebot import logger, scheduler

from src.utils.helpers import get_first_bot

from .config import config


class Calender:
    def __init__(self):
        # 动态的地址
        self._url = 'https://tools.yobot.win/calender/cn.json'
        # 定时任务
        self._job = None
        # 日程表
        self._timeline = {}

        # 根据配置启动
        if config.push_calender:
            self.enable()

    def enable(self):
        """ 开启日程自动推送 """
        logger.info('初始化 公主连结Re:Dive 日程推送')
        self._job = scheduler.add_job(
            self.push_calender,
            'cron',
            hour=config.calender_hour,
            minute=config.calender_minute,
            second=config.calender_second,
            id='push_calender'
        )
        config.push_calender = True

    def disable(self):
        """ 关闭日程自动推送 """
        self._job.remove()
        self._job = None
        config.push_calender = False

    @property
    def is_enabled(self):
        """ 是否启用日程自动推送 """
        if self._job:
            return True
        else:
            return False

    async def refresh_calender(self) -> None:
        """ 获取最新的日程表 """
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(self._url)
                if r.status_code != 200:
                    # 如果 HTTP 响应状态码不是 200，说明调用失败
                    return None

                for event in r.json():
                    start_time = datetime.strptime(
                        event['start_time'], '%Y/%m/%d %H:%M:%S'
                    )
                    end_time = datetime.strptime(
                        event['end_time'], '%Y/%m/%d %H:%M:%S'
                    )
                    name = event['name']
                    self.add_event(start_time, end_time, name)

                logger.info('公主连结Re:Dive 日程表刷新成功')
        except (httpx.HTTPError, KeyError) as e:
            logger.error(f'获取日程表出错，{e}')
            # 抛出上面任何异常，说明调用失败
            return None

    def add_event(
        self, start_time: datetime, end_time: datetime, name: str
    ) -> None:
        """ 添加日程至日程表 """
        t = start_time
        while t <= end_time:
            daystr = t.strftime('%Y%m%d')
            if daystr not in self._timeline:
                self._timeline[daystr] = list()
            self._timeline[daystr].append(name)
            t += timedelta(days=1)

    async def push_calender(self):
        """ 推送日程 """
        logger.info('推送今日 公主连结Re:Dive 日程')

        await self.refresh_calender()

        date = datetime.now()
        events = self._timeline.get(date.strftime('%Y%m%d'))
        if events is None:
            events_str = '无活动或无数据'
        else:
            events_str = "\n".join(events)

        reply = '公主连结Re:Dive 今日活动：\n{}'.format(events_str)
        for group_id in config.group_id:
            await get_first_bot().send_msg(
                message_type='group', group_id=group_id, message=reply
            )

    async def get_week_events(self) -> str:
        """ 获取日程表 """
        await self.refresh_calender()

        reply = '一周日程：'
        date = datetime.now()

        for _ in range(7):
            events = self._timeline.get(date.strftime('%Y%m%d'), ())
            events_str = '\n⨠'.join(events)
            if events_str == '':
                events_str = '没有记录'
            daystr = date.strftime('%Y%m%d')
            reply += f'\n======{daystr}======\n⨠{events_str}'
            date += timedelta(days=1)

        reply += '\n\n更多日程：https://tools.yobot.win/calender/#cn'

        return reply


calender_data = Calender()
