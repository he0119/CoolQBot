from datetime import datetime, timedelta
from typing import Optional, TypedDict

from nonebot.adapters.cqhttp import Message

from src.utils.helpers import render_expression
from dateutil import parser
from .config import DATA


def get_first_connect_message():
    """ 根据当前时间返回对应消息 """
    hour = datetime.now().hour

    if hour > 18 or hour < 6:
        return '晚上好呀！'

    if hour > 13:
        return '下午好呀！'

    if hour > 11:
        return '中午好呀！'

    return '早上好呀！'


EXPR_MORNING = (
    '早上好呀~>_<~\n{message}',
    '大家早上好呀！\n{message}',
    '朋友们早上好！\n{message}',
    '群友们早上好！\n{message}',
 ) # yapf: disable

class HolidayInfo(TypedDict):
    """ 节假日信息 """
    name: str
    date: datetime
    # 是否为节假日
    holiday: bool
    # 调休是否在节假日后
    # 如果是节假日则默认为真
    after: bool


def process_data(data: dict) -> dict:
    # 提取所需要的数据，今年和明年的节日数据
    # 因为明年元旦的节假日可能从今年开始
    now = datetime.now()
    holidays: dict[str, dict] = {}
    for year in range(now.year, now.year + 2):
        if str(year) in data:
            holidays.update(data[str(year)])
    return holidays


HOLIDAYS_DATA = DATA.network_file(
    'https://cdn.jsdelivr.net/gh/he0119/coolqbot@change/morning/src/plugins/morning/holidays.json',
    'holidays.json',
    process_data,
)


async def get_recent_holiday() -> Optional[HolidayInfo]:
    """ 获取最近的节假日

    返回最近的节假日信息
    """
    data = await HOLIDAYS_DATA.data
    if not data:
        raise

    now = datetime.now()

    holidays: list[HolidayInfo] = []
    for date in data:
        holidays += process_holiday(parser.parse(date), data[date])
    holidays.sort(key=lambda info: info['date'])

    for holiday in holidays:
        if holiday['date'] > now:
            return holiday


async def get_recent_workday() -> Optional[HolidayInfo]:
    """ 获取最近的节假日调休

    返回最近的节假日调休信息
    """
    data = await HOLIDAYS_DATA.data
    if not data:
        raise

    now = datetime.now()

    workdays: list[HolidayInfo] = []
    for date in data:
        workdays += process_workday(parser.parse(date), data[date])
    workdays.sort(key=lambda info: info['date'])

    for workday in workdays:
        if workday['date'] > now:
            return workday


def process_holiday(date: datetime, data: dict) -> list[HolidayInfo]:
    """ 处理节假日数据 """
    holidays: list[HolidayInfo] = []
    for i in range(data['duration']):
        holidays.append(
            HolidayInfo(
                name=data['name'],
                date=date + timedelta(days=i),
                holiday=True,
                after=False,
            ))
    return holidays


def process_workday(date: datetime, data: dict) -> list[HolidayInfo]:
    """ 处理节假日调休数据 """
    workdays: list[HolidayInfo] = []
    if data['workdays']:
        for workday in data['workdays']:
            workday = parser.parse(workday)
            workdays.append(
                HolidayInfo(
                    name=data['name'],
                    date=workday,
                    holiday=False,
                    after=workday > date,
                ))
    return workdays


async def get_moring_message() -> Message:
    """ 获得早上问好

    日期不同，不同的问候语
    """
    now = datetime.now()
    now = datetime(now.year, now.month, now.day)

    message = ''

    holiday = await get_recent_holiday()
    workday = await get_recent_workday()
    if holiday:
        # 周末的日期，确认是否在周末，是否和节假日重叠

        # 节日距离现在还有多少天
        rest = (holiday['date'] - now).days

    return render_expression(EXPR_MORNING, message=message)
