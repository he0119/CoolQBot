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
    "bind",
    aliases={("原神", "绑定"), ("原神", "绑定账号")},
    permission=PRIVATE,
)
bind_cmd.__doc__ = """
原神

绑定账号
/ys.bind
绑定账号（直接附带 Cookie）
/ys.bind cookie=1234567890

获取 Cookie 的方法详见:
https://github.com/Womsxd/YuanShen_User_Info
"""


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
daily_note_cmd = genshin.command(
    "dailynote",
    aliases={("原神", "实时便笺"), ("原神", "便笺")},
)
daily_note_cmd.__doc__ = """
原神 实时便笺

获取实时便笺
/ys.dailynote
"""


@daily_note_cmd.handle()
async def daily_note(event: MessageEvent):
    """实时便笺信息"""
    cookie = get_cookie(event.user_id)
    if not cookie:
        await daily_note_cmd.finish("你还没有绑定账号，请私聊机器人绑定账号绑定后查询")

    genshin = Genshin(cookie)
    note = await genshin.daily_note()
    await daily_note_cmd.finish(note)


# endregion
