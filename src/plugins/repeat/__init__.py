""" 复读插件

按照一定条件复读聊天
拥有一些配套功能，如复读排行榜，排行榜历史记录，复读状态
"""
from nonebot import CommandGroup

from coolqbot import PluginData

cg = CommandGroup('repeat')

DATA = PluginData('repeat', config=True)

from . import commands, nlp
