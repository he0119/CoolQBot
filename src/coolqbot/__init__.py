""" 机器人

需要暴露给外面的东西
"""
from .bot import CoolQBot
from .plugin import MessageType

bot = CoolQBot(enable_http_post=False)
