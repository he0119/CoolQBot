""" 绑定账号 """
from nonebot.adapters import Event, Message
from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText, CommandArg
from nonebot.plugin import PluginMetadata

from ... import genshin, set_cookie

__plugin_meta__ = PluginMetadata(
    name="原神绑定",
    description="绑定原神账号",
    usage="绑定账号\n/ys.bind\n绑定账号（直接附带 Cookie）\n/ys.bind cookie=1234567890\n\n获取 Cookie 的方法详见:\nhttps://github.com/Womsxd/YuanShen_User_Info",
)

bind_cmd = genshin.command(
    "bind",
    aliases={("原神", "绑定"), ("原神", "绑定账号")},
)


@bind_cmd.handle()
async def bind_handle_first_receive(matcher: Matcher, arg: Message = CommandArg()):
    if arg.extract_plain_text():
        matcher.set_arg("cookie", arg)


@bind_cmd.got("cookie", "请输入米游社的 cookie")
async def bind_handle(event: Event, cookie: str = ArgPlainText()):
    set_cookie(event.get_user_id(), cookie)
    await bind_cmd.finish("绑定成功！")
