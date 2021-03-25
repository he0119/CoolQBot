import random
from typing import List, Optional, Sequence

from nonebot import get_bots
from nonebot.adapters import Bot
from nonebot.adapters.cqhttp import Message

from .typing import Expression_T


def render_expression(expr: Expression_T, *args, **kwargs) -> Message:
    """
    Render an expression to message string.
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


def get_first_bot() -> Optional[Bot]:
    """ 获得连接的第一个 bot """
    if get_bots():
        return list(get_bots().values())[0]


def strtobool(val: str) -> bool:
    """ 将文本转化成布尔值

    如果是 y, yes, t, true, on, 1, 是, 确认, 开, 返回 True;
    其他的均为返回 False;
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1', '是', '确认', '开'):
        return True
    return False


def strtogroupid(val: str) -> List[int]:
    """ 转换文本至群ID列表

    群ID用空格隔开
    """
    if val:
        return list(map(int, val.split()))
    return []


def groupidtostr(val: List[int]) -> str:
    """ 群ID列表转换至文本

    群ID用空格隔开
    """
    return ' '.join(map(str, val))
