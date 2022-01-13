""" 原神

实时便笺
"""
from nonebot import CommandGroup

from .api import Genshin

genshin = CommandGroup("ys")

daily_note_cmd = genshin.command("daily_note", aliases={("原神", "实时便笺"), ("ys", "便笺")})


@daily_note_cmd.handle()
async def daily_note():
    """实时便笺信息"""
    genshin = Genshin("")
    note = await genshin.daily_note()
    await daily_note_cmd.finish(note)
