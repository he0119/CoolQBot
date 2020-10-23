""" 帮助 """
import inspect
from functools import reduce

from nonebot import get_loaded_plugins, on_command
from nonebot.typing import Bot, Event

help = on_command('help', priority=1, block=True)
help.__doc__ = """
/help
获取帮助
"""


@help.handle()
async def handle(bot: Bot, event: Event, state: dict):
    plugins = get_loaded_plugins()
    matchers = reduce(lambda x, y: x.union(y.matcher), plugins, set())
    docs = "命令列表：\n"
    docs += "\n".join(
        map(
            lambda x: inspect.cleandoc(x.__doc__),
            filter(lambda x: x.__doc__, matchers)
        )
    )
    await help.finish(docs)
