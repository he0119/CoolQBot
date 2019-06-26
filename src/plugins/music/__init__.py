""" 音乐插件
"""
from nonebot import on_command, CommandSession
from nonebot import on_natural_language, NLPSession, IntentCommand
from nonebot.helpers import render_expression

from .netease import call_netease_api

# 定义无法获取歌曲时的「表达（Expression）」
EXPR_NOT_FOUND = ('为什么找不到匹配的歌呢！', '似乎哪里出错了，找不到你想点的歌 ~><~')


@on_command('music', aliases={'点歌'}, only_to_me=False)
async def music(session: CommandSession):
    name = session.get('name', prompt='你想听哪首歌呢？')
    music = await call_netease_api(name)
    if music:
        await session.send(music)
    else:
        await session.send(render_expression(EXPR_NOT_FOUND), at_sender=True)


@music.args_parser
async def _(session: CommandSession):
    stripped_arg = session.current_arg_text.strip()

    if session.is_first_run:
        if stripped_arg:
            session.state['name'] = stripped_arg
        return

    if not stripped_arg:
        session.pause('歌曲名不能为空呢，请重新输入！')

    session.state[session.current_key] = stripped_arg


@on_natural_language(keywords={'点歌'})
async def _(session: NLPSession):
    # 去掉消息首尾的空白符以及开头的点歌两字
    stripped_msg = session.msg_text.strip()[2:].strip()

    return IntentCommand(90.0, 'music', current_arg=stripped_msg or '')
