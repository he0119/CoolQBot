""" 音乐插件
"""
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgStr, CommandArg, Depends

from src.utils.helpers import render_expression

from .netease import call_netease_api

# 无法获取歌曲时的回答
EXPR_NOT_FOUND = (
    "为什么找不到匹配的歌呢！",
    "似乎哪里出错了，找不到你想点的歌 ~><~",
    "没有找到，要不要换个关键字试试？",
)

music_cmd = on_command("music", aliases={"点歌"})
music_cmd.__doc__ = """
点歌

参数为歌曲相关信息
/music Sagitta luminis
如果仅凭歌曲名称无法获得正确歌曲时
可以尝试在后面加上歌手名称或其他信息
/music Sagitta luminis 梶浦由記
"""


@music_cmd.handle()
async def music_handle_first_receive(matcher: Matcher, arg: Message = CommandArg()):
    args = str(arg).strip()

    if args:
        matcher.set_arg("name", Message(args))


async def music_args_parser(name: Message = Arg()):
    if not name.extract_plain_text():
        await music_cmd.reject("歌曲名不能为空呢，请重新输入！")


@music_cmd.got("name", prompt="你想听哪首歌呢？", parameterless=[Depends(music_args_parser)])
async def music_handle(name: str = ArgStr()):
    music_message = await call_netease_api(name)
    if music_message:
        await music_cmd.finish(music_message)
    else:
        await music_cmd.finish(render_expression(EXPR_NOT_FOUND), at_sender=True)
