from typing import Union
from collections.abc import Callable, Sequence

Expression_T = Union[str, Sequence[str], Callable[..., str]]
