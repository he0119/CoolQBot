import hashlib
import random
from typing import Sequence

from nonebot.adapters.cqhttp import Event

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
