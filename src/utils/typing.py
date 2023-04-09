from collections.abc import Callable, Sequence
from typing import Union

Expression_T = Union[str, Sequence[str], Callable[..., str]]
