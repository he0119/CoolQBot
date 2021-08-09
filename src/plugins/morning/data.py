from datetime import datetime, timedelta
from typing import Optional, TypedDict

from dateutil import parser
from nonebot.adapters.cqhttp import Message

from src.utils.helpers import render_expression

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
    'https://cdn.jsdelivr.net/gh/he0119/coolqbot@master/src/plugins/morning/holidays.json',
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
    now = datetime(now.year, now.month, now.day)

    holidays: list[HolidayInfo] = []
    for date in data:
        holidays += process_holiday(parser.parse(date), data[date])
    holidays.sort(key=lambda info: info['date'])

    for holiday in holidays:
        if holiday['date'] >= now:
            return holiday


async def get_recent_workday() -> Optional[HolidayInfo]:
    """ 获取最近的节假日调休

    返回最近的节假日调休信息
    """
    data = await HOLIDAYS_DATA.data
    if not data:
        raise

    now = datetime.now()
    now = datetime(now.year, now.month, now.day)

    workdays: list[HolidayInfo] = []
    for date in data:
        workdays += process_workday(parser.parse(date), data[date])
    workdays.sort(key=lambda info: info['date'])

    for workday in workdays:
        if workday['date'] >= now:
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


async def get_holiday_message() -> str:
    """ 获得问候语

    日期不同，不同的问候语，参考 http://timor.tech/api/holiday/tts

    今天就是劳动节，好好玩吧！
    明天就是劳动节了，开不开心？
    今天是劳动节前调休，马上就是劳动节了，还有6天，加油！
    劳动节才刚刚过完。今天是劳动节后调休，老老实实上班吧。
    今天是周六，放松一下吧！

    明天是中秋节前调休，记得设置好闹钟，上班别迟到了。再过2天是中秋节。
    还有2天就是周六了，先好好工作吧！最近的一个节日是劳动节。还要9天。早着呢！
    还有3天就是劳动节了，别着急。
    """
    holiday = await get_recent_holiday()
    workday = await get_recent_workday()

    # 默认值
    workday_rest = -1
    holiday_rest = -1

    now = datetime.now()
    now = datetime(now.year, now.month, now.day)
    # 周末距离现在还有多少天
    weekend_rest = 5 - now.weekday()
    if workday:
        # 调休距离现在还有多少天
        workday_rest = (workday['date'] - now).days
    if holiday:
        # 节日距离现在还有多少天
        holiday_rest = (holiday['date'] - now).days

    # 根据节假日与调休生成问候语

    # 先处理今天是节假日的情况
    if holiday and holiday_rest == 0:
        return f'今天就是{holiday["name"]}，好好玩吧！'

    # 处理今天是调休的情况
    if workday and workday_rest == 0:
        after = workday['after']
        if after:
            return f'{workday["name"]}才刚刚过完。今天是{workday["name"]}后调休，老老实实上班吧。'
        # 调休的第二天就是节假日
        elif holiday and holiday_rest == 1:
            return f'今天是{workday["name"]}前调休，明天就是{holiday["name"]}了，加油！'
        elif holiday:
            return f'今天是{workday["name"]}前调休，马上就是{holiday["name"]}了，还有{holiday_rest}天，加油！'

    # 处理今天是周末，且不是节假日或者调休的情况
    if now.weekday() == 5:
        return '今天是星期六，放松一下吧！'
    if now.weekday() == 6:
        return '今天是星期日，放松一下吧！'

    # 如果今天是星期五且最近两天有调休
    if workday and workday_rest < 3 and now.weekday() == 4:
        after = workday['after']
        if after:
            weekend_name = "周六" if workday_rest == 1 else "周日"
            if holiday:
                return f'很遗憾的告诉您，这{weekend_name}要{workday["name"]}后调休。最近的一个节日是{holiday["name"]}。还要{holiday_rest}天。早着呢！'
            else:
                return f'很遗憾的告诉您，这{weekend_name}要{workday["name"]}后调休。'
        else:
            if workday_rest == 1:
                return f'明天是{workday["name"]}前调休，记得设置好闹钟，上班别迟到了。再过{holiday_rest}天是{workday["name"]}。'
            else:
                return f'明天就是周六了，今天努力工作哦！周日是{workday["name"]}前调休，记得设置好闹钟，上班别迟到了。再过{holiday_rest}天是{workday["name"]}。'

    # 处理第二天是节假日的情况
    if holiday and holiday_rest == 1:
        return f'明天就是{holiday["name"]}了，开不开心？'

    # 处理还有五天内就节假日的情况
    if holiday and holiday_rest < 6:
        return f'还有{holiday_rest}天就是{holiday["name"]}了，别着急。'

    # 其他所有情况
    if holiday:
        return f'还有{weekend_rest}天就是周六了，先好好工作吧！最近的一个节日是{holiday["name"]}。还要{holiday_rest}天。早着呢！'

    return f'还有{weekend_rest}天就是周六了，先好好工作吧！'


async def get_moring_message() -> Message:
    """ 获得早上问好 """
    message = await get_holiday_message()
    return render_expression(EXPR_MORNING, message=message)
