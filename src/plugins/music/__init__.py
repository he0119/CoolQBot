"""音乐插件"""

from nonebot import require
from nonebot.adapters.onebot.v11 import Bot
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension

from src.utils.helpers import render_expression

from .netease import call_netease_api

__plugin_meta__ = PluginMetadata(
    name="音乐",
    description="通过网易云音乐点歌",
    usage="""参数为歌曲相关信息
/music Sagitta luminis
如果仅凭歌曲名称无法获得正确歌曲时
可以尝试在后面加上歌手名称或其他信息
/music Sagitta luminis 梶浦由記""",
    supported_adapters={"~onebot.v11"},
)


# 无法获取歌曲时的回答
EXPR_NOT_FOUND = (
    "为什么找不到匹配的歌呢！",
    "似乎哪里出错了，找不到你想点的歌 ~><~",
    "没有找到，要不要换个关键字试试？",
)

music_cmd = on_alconna(
    Alconna(
        "点歌",
        Args["keywords?#音乐名称或信息", str],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"music"},
    use_cmd_start=True,
    block=True,
    extensions=[TelegramSlashExtension(), DiscordSlashExtension()],
)


@music_cmd.handle()
async def music_handle_first_receive(bot: Bot, keywords: Match[str]):
    if keywords.available:
        music_cmd.set_path_arg("keywords", keywords.result)


@music_cmd.got_path("keywords", prompt="你想听哪首歌呢？")
async def music_handle(keywords: str):
    music_message = await call_netease_api(keywords)
    if music_message:
        await music_cmd.finish(music_message)
    else:
        await music_cmd.finish(render_expression(EXPR_NOT_FOUND), at_sender=True)
