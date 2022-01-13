""" 原神

实时便笺
"""
from nonebot import CommandGroup
from nonebot.adapters.onebot.v11 import Message, MessageEvent, PrivateMessageEvent
from nonebot.adapters.onebot.v11.permission import PRIVATE
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg

from .api import Genshin
from .config import get_cookie, set_cookie

genshin = CommandGroup("ys")

# region 绑定账号
bind_cmd = genshin.command(
    "bind", aliases={("原神", "绑定"), ("ys", "绑定账号")}, permission=PRIVATE
)


@bind_cmd.handle()
async def bind_handle_first_receive(matcher: Matcher, arg: Message = CommandArg()):
    if arg.extract_plain_text():
        matcher.set_arg("cookie", arg)


@bind_cmd.got("cookie", "请输入米游社的 cookie")
async def bind_handle(event: PrivateMessageEvent, cookie: str = ArgPlainText()):
    set_cookie(event.user_id, cookie)
    await bind_cmd.finish("绑定成功！")


# endregion

# region 实时便笺
daily_note_cmd = genshin.command("daily_note", aliases={("原神", "实时便笺"), ("ys", "便笺")})


@daily_note_cmd.handle()
async def daily_note(event: MessageEvent):
    """实时便笺信息"""
    if cookie := get_cookie(event.user_id):
        await daily_note_cmd.finish("你还没有绑定账号，请私聊机器人 /原神.绑定")

    genshin = Genshin(cookie)
    note = await genshin.daily_note()
    await daily_note_cmd.finish(note)


# endregion
