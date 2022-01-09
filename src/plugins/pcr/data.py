""" 日程表

https://pcrbot.github.io/pcr-calendar/#cn
"""
from datetime import datetime, timedelta

import httpx
from nonebot.log import logger


class Calendar:
    def __init__(self):
        # 动态的地址
        self._url = "https://pcrbot.github.io/calendar-updater-action/cn.json"
        # 日程表
        self._timeline: dict[str, set[str]] = {}
        self._timeline_update_time: datetime = datetime.now()

    async def refresh_calendar(self) -> None:
        """获取最新的日程表"""
        if self._timeline:
            # 最近四小时内才更新的不用再次更新
            if self._timeline_update_time > datetime.now() - timedelta(hours=4):
                return
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(self._url)
                rjson = r.json()

                # 清除以前的时间线
                self._timeline.clear()
                for event in rjson:
                    start_time = datetime.strptime(
                        event["start_time"], "%Y/%m/%d %H:%M:%S"
                    )
                    end_time = datetime.strptime(event["end_time"], "%Y/%m/%d %H:%M:%S")
                    name = event["name"]
                    self.add_event(start_time, end_time, name)

                self._timeline_update_time = datetime.now()
                logger.info("公主连结Re:Dive 日程表刷新成功")
        except (httpx.HTTPError, KeyError) as e:
            logger.error(f"获取日程表出错，{e}")
            # 抛出上面任何异常，说明调用失败
            return

    def add_event(self, start_time: datetime, end_time: datetime, name: str) -> None:
        """添加日程至日程表"""
        t = start_time
        while t <= end_time:
            daystr = t.strftime("%Y%m%d")
            if daystr not in self._timeline:
                self._timeline[daystr] = set()
            self._timeline[daystr].add(name)
            t += timedelta(days=1)

    async def get_week_events(self) -> str:
        """获取日程表"""
        await self.refresh_calendar()

        reply = "一周日程："
        date = datetime.now()

        for _ in range(7):
            events = self._timeline.get(date.strftime("%Y%m%d"), ())
            events_str = "\n⨠".join(sorted(events))
            if events_str == "":
                events_str = "没有记录"
            daystr = date.strftime("%Y%m%d")
            reply += f"\n======{daystr}======\n⨠{events_str}"
            date += timedelta(days=1)

        reply += "\n\n更多日程：https://pcrbot.github.io/pcr-calendar/#cn"

        return reply


calendar = Calendar()
