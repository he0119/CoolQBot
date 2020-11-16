import hashlib
import random
from typing import List, Optional, Sequence

from nonebot import get_bots
from nonebot.typing import Bot, Event

from .typing import Expression_T


def render_expression(expr: Expression_T, *args, **kwargs) -> str:
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
    return result.format(*args, **kwargs)


def context_id(
    event: Event, *, mode: str = 'default', use_hash: bool = False
) -> str:
    """
    Calculate a unique id representing the context of the given event.
    mode:
      default: one id for one context
      group: one id for one group or discuss
      user: one id for one user
    :param event: the event object
    :param mode: unique id mode: "default", "group", or "user"
    :param use_hash: use md5 to hash the id or not
    """
    ctx_id = ''
    if mode == 'default':
        if event.group_id:
            ctx_id = f'/group/{event.group_id}'
        if event.user_id:
            ctx_id += f'/user/{event.user_id}'
    elif mode == 'group':
        if event.group_id:
            ctx_id = f'/group/{event.group_id}'
        elif event.user_id:
            ctx_id = f'/user/{event.user_id}'
    elif mode == 'user':
        if event.user_id:
            ctx_id = f'/user/{event.user_id}'

    if ctx_id and use_hash:
        ctx_id = hashlib.md5(ctx_id.encode('ascii')).hexdigest()
    return ctx_id


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
