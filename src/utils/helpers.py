import random
from datetime import timedelta
from typing import Sequence, Union

from nonebot.adapters.onebot.v11 import Message
from nonebot.matcher import Matcher
from nonebot.params import Arg
from nonebot.typing import T_State

from .typing import Expression_T


def render_expression(expr: Expression_T, *args, **kwargs) -> Message:
    """Render an expression to message string.

    :param expr: expression to render
    :param args: positional arguments used in str.format()
    :param kwargs: keyword arguments used in str.format()
    :return: the rendered message
    """
    result: str
    if callable(expr):
        result = expr(*args, **kwargs)
    elif isinstance(expr, Sequence) and not isinstance(expr, str):
        result = random.choice(expr)
    else:
        result = expr
    return Message(result.format(*args, **kwargs))


def strtobool(val: str) -> bool:
    """将文本转化成布尔值

    如果是 y, yes, t, true, on, 1, 是, 确认, 开, 返回 True;
    其他的均为返回 False;
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1", "是", "确认", "开"):
        return True
    return False


def parse_int(key: str):
    """解析数字，并将结果存入 state 中"""

    async def _key_parser(
        matcher: Matcher, state: T_State, input: Union[int, Message] = Arg(key)
    ):
        if isinstance(input, int):
            return

        plaintext = input.extract_plain_text()
        if not plaintext.isdigit():
            await matcher.reject_arg(key, "请只输入数字，不然我没法理解呢！")
        state[key] = int(plaintext)

    return _key_parser


def parse_bool(key: str):
    """解析布尔值，并将结果存入 state 中"""

    async def _key_parser(state: T_State, input: Union[bool, Message] = Arg(key)):
        if isinstance(input, bool):
            return

        plaintext = input.extract_plain_text()
        state[key] = strtobool(plaintext)

    return _key_parser


def timedelta_to_chinese(timedelta: timedelta) -> str:
    """将 timedelta 转换为中文时间"""
    days = timedelta.days
    hours = timedelta.seconds // 3600
    minutes = (timedelta.seconds % 3600) // 60
    seconds = timedelta.seconds % 60

    time_str = ""
    if days:
        if days == 1:
            time_str += "明天"
        elif days == 2:
            time_str += "后天"
        else:
            time_str += f"{days}天"
    if hours:
        time_str += f"{hours}小时"
    if minutes:
        time_str += f"{minutes}分钟"
    if seconds:
        time_str += f"{seconds}秒"
    return time_str
