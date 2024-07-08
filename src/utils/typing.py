from collections.abc import Callable, Sequence

Expression_T = str | Sequence[str] | Callable[..., str]
