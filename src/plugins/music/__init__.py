""" 音乐插件
"""
from nonebot import on_command
from nonebot.typing import Bot, Event

from src.utils.helpers import render_expression

from .netease import call_netease_api

# 定义无法获取歌曲时的「表达（Expression）」
EXPR_NOT_FOUND = ('为什么找不到匹配的歌呢！', '似乎哪里出错了，找不到你想点的歌 ~><~')

music = on_command('music', aliases={'点歌'}, priority=1, block=True)


@music.handle()
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    if stripped_arg:
        state['name'] = stripped_arg


@music.got('name', prompt='你想听哪首歌呢？')
async def _(bot: Bot, event: Event, state: dict):
    music_str = await call_netease_api(state['name'])
    if music_str:
        await music.finish(music_str)
    else:
        await music.finish(render_expression(EXPR_NOT_FOUND), at_sender=True)


@music.args_parser
async def _(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    if not stripped_arg:
        await music.reject('歌曲名不能为空呢，请重新输入！')

    state['name'] = stripped_arg
