from datetime import date, timedelta
from typing import TypedDict

from dateutil import parser
from nonebot_plugin_datastore import get_plugin_data

from src.utils.helpers import render_expression

plugin_data = get_plugin_data()


class HolidayInfo(TypedDict):
    """节假日信息"""

    name: str
    date: date
    # 是否为节假日
    holiday: bool
    # 调休是否在节假日后
    # 如果是节假日则默认为真
    after: bool


def process_data(data: dict) -> dict:
    # 提取所需要的数据，今年和明年的节日数据
    # 因为明年元旦的节假日可能从今年开始
    today = date.today()
    holidays: dict[str, dict] = {}
    for year in range(today.year, today.year + 2):
        if str(year) in data:
            holidays.update(data[str(year)])
    return holidays


HOLIDAYS_DATA = plugin_data.network_file(
    "https://raw.fastgit.org/he0119/CoolQBot/master/src/plugins/morning/holidays.json",
    "holidays.json",
    process_data,
)


async def get_recent_holiday() -> HolidayInfo | None:
    """获取最近的节假日

    返回最近的节假日信息
    """
    data = await HOLIDAYS_DATA.data
    if not data:
        raise Exception("获取节假日数据失败")

    today = date.today()

    holidays: list[HolidayInfo] = []
    for date_str in data:
        holidays += process_holiday(parser.parse(date_str).date(), data[date_str])
    holidays.sort(key=lambda info: info["date"])

    for holiday in holidays:
        if holiday["date"] >= today:
            return holiday


async def get_recent_workday() -> HolidayInfo | None:
    """获取最近的节假日调休

    返回最近的节假日调休信息
    """
    data = await HOLIDAYS_DATA.data
    if not data:
        raise Exception("获取节假日数据失败")

    today = date.today()

    workdays: list[HolidayInfo] = []
    for date_str in data:
        workdays += process_workday(parser.parse(date_str).date(), data[date_str])
    workdays.sort(key=lambda info: info["date"])

    for workday in workdays:
        if workday["date"] >= today:
            return workday


def process_holiday(date: date, data: dict) -> list[HolidayInfo]:
    """处理节假日数据"""
    holidays: list[HolidayInfo] = []
    for i in range(data["duration"]):
        holidays.append(
            HolidayInfo(
                name=data["name"],
                date=date + timedelta(days=i),
                holiday=True,
                after=False,
            )
        )
    return holidays


def process_workday(date: date, data: dict) -> list[HolidayInfo]:
    """处理节假日调休数据"""
    workdays: list[HolidayInfo] = []
    if data["workdays"]:
        for workday in data["workdays"]:
            workday = parser.parse(workday).date()
            workdays.append(
                HolidayInfo(
                    name=data["name"],
                    date=workday,
                    holiday=False,
                    after=workday > date,
                )
            )
    return workdays


async def get_holiday_message() -> str:
    """获得问候语

    日期不同，不同的问候语，参考 http://timor.tech/api/holiday/tts

    节假日/周末：
        今天就是劳动节，好好玩吧！
        今天是周六，放松一下吧！
    调休：
        今天是劳动节前调休，马上就是劳动节了，还有6天，加油！
        劳动节才刚刚过完。今天是劳动节后调休，老老实实上班吧。
    工作日：
        明天就是劳动节了，开不开心？
        明天是中秋节前调休，记得设置好闹钟，上班别迟到了。再过2天是中秋节。
        还有2天就是周六了，先好好工作吧！最近的一个节日是劳动节，还要9天。早着呢！
        还有3天就是劳动节了，别着急。
    """
    holiday = await get_recent_holiday()
    workday = await get_recent_workday()

    # 默认值
    workday_rest = -1
    holiday_rest = -1

    today = date.today()

    # 周末距离现在还有多少天
    weekend_rest = 5 - today.weekday()
    if workday:
        # 调休距离现在还有多少天
        workday_rest = (workday["date"] - today).days
    if holiday:
        # 节日距离现在还有多少天
        holiday_rest = (holiday["date"] - today).days

    # 根据节假日与调休生成问候语

    # 先处理今天是节假日的情况
    if holiday and holiday_rest == 0:
        return f'今天就是{holiday["name"]}，好好玩吧！'

    # 处理今天是调休的情况
    if workday and workday_rest == 0:
        if workday["after"]:
            return f'{workday["name"]}才刚刚过完。今天是{workday["name"]}后调休，老老实实上班吧。'
        # 不需要考虑节假日不存在的情况
        # 因为如果调休在节假日前，说明调休后一定有节假日
        # 调休的第二天就是节假日
        elif holiday_rest == 1:
            return f'今天是{workday["name"]}前调休，明天就是{workday["name"]}了，加油！'
        else:
            return (
                f'今天是{workday["name"]}前调休，马上就是{workday["name"]}了，还有{holiday_rest}天，加油！'
            )

    # 处理今天是周末，且不是节假日或者调休的情况
    if today.weekday() == 5:
        return "今天是星期六，放松一下吧！"
    if today.weekday() == 6:
        return "今天是星期日，放松一下吧！"

    # 处理今天是星期五且最近两天有调休的情况
    if workday and workday_rest < 3 and today.weekday() == 4:
        if workday["after"]:
            weekend_name = "周六" if workday_rest == 1 else "周日"
            if holiday:
                return f'很遗憾的告诉您，这{weekend_name}要{workday["name"]}后调休。最近的一个节日是{holiday["name"]}。还要{holiday_rest}天。早着呢！'
            else:
                return f'很遗憾的告诉您，这{weekend_name}要{workday["name"]}后调休。'
        # 不需要考虑节假日不存在的情况
        # 因为如果调休在节假日前，说明调休后一定有节假日
        elif workday_rest == 1:
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
        return f'还有{weekend_rest}天就是周六了，先好好工作吧！最近的一个节日是{holiday["name"]}，还要{holiday_rest}天。早着呢！'

    return f"还有{weekend_rest}天就是周六了，先好好工作吧！"


EXPR_MORNING = (
    "早上好呀~>_<~\n{message}",
    "大家早上好呀！\n{message}",
    "朋友们早上好！\n{message}",
    "群友们早上好！\n{message}",
)


async def get_moring_message() -> str:
    """获得早上问好"""
    message = await get_holiday_message()
    return render_expression(EXPR_MORNING, message=message)
