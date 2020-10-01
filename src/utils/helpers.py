import random
from typing import Sequence

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
