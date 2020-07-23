""" 最终幻想XIV

一些最终幻想XIV相关的指令
"""
from nonebot import CommandGroup

from coolqbot import PluginData

__plugin_name__ = 'ff14'

cg = CommandGroup('ff14')

DATA = PluginData('ff14', config=True)

from . import commands
