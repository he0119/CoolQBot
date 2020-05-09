""" 复读插件

按照一定条件复读聊天
拥有一些配套功能，如复读排行榜，排行榜历史记录，复读状态
"""
from nonebot import CommandGroup

from coolqbot import PluginData

__plugin_name__ = 'repeat'
__plugin_usage__ = r"""
人类本质

用来模仿人类，同时提供排行榜，历史记录和记录复读状态功能。

例如：
-------排行榜---------
/rank
/rank 30n0
-------历史记录-------
/history
/history 2020-01
/history 2020-01-01
-------状态-----------
/status

命令均需要在群里使用。
""".strip()

cg = CommandGroup('repeat')

DATA = PluginData('repeat', config=True)

from . import commands, nlp
