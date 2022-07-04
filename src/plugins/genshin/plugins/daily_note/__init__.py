""" 实时便笺 """

from nonebot.adapters import Event
from nonebot.plugin import PluginMetadata

from ... import Genshin, genshin, get_cookie

__plugin_meta__ = PluginMetadata(
    name="实时便笺",
    description="获取最新的实时便笺",
    usage="获取实时便笺\n/ys.dailynote\n/原神.便笺",
)


# region 实时便笺
daily_note_cmd = genshin.command(
    "dailynote",
    aliases={("原神", "实时便笺"), ("原神", "便笺")},
)


@daily_note_cmd.handle()
async def daily_note(event: Event):
    """实时便笺信息"""
    cookie = get_cookie(event.get_user_id())
    if not cookie:
        await daily_note_cmd.finish("你还没有绑定账号，请私聊机器人绑定账号绑定后查询")

    genshin = Genshin(cookie)
    note = await genshin.daily_note()
    await daily_note_cmd.finish(note)
