""" 音乐插件
"""
from nonebot import on_command
from nonebot.typing import Bot, Event

from src.utils.helpers import render_expression

from .netease import call_netease_api

# 无法获取歌曲时的回答
EXPR_NOT_FOUND = (
    '为什么找不到匹配的歌呢！',
    '似乎哪里出错了，找不到你想点的歌 ~><~',
    '没有找到，要不要换个关键字试试？'
) # yapf: disable

music_cmd = on_command('music', aliases={'点歌'}, block=True)
music_cmd.__doc__ = """
music 点歌

点歌

参数为歌曲相关信息
/music Sagitta luminis
如果仅凭歌曲名称无法获得正确歌曲时
可以尝试在后面加上歌手名称或其他信息
/music Sagitta luminis 梶浦由記
"""


@music_cmd.handle()
async def _(bot: Bot, event: Event, state: dict):
    args = str(event.message).strip()

    if args:
        state['name'] = args


@music_cmd.got('name', prompt='你想听哪首歌呢？')
async def _(bot: Bot, event: Event, state: dict):
    music_str = await call_netease_api(state['name'])
    if music_str:
        await music_cmd.finish(music_str)
    else:
        await music_cmd.finish(
            render_expression(EXPR_NOT_FOUND), at_sender=True
        )


@music_cmd.args_parser
async def _(bot: Bot, event: Event, state: dict):
    args = str(event.message).strip()

    if not args:
        await music_cmd.reject('歌曲名不能为空呢，请重新输入！')

    state[state['_current_key']] = args
