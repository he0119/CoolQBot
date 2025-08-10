"""音乐插件"""

from nonebot import logger, require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

from .config import plugin_config

if not plugin_config.alisten_server_url or not plugin_config.alisten_house_id:
    logger.warning("alisten 未配置，插件已禁用")

require("nonebot_plugin_alconna")
require("nonebot_plugin_user")
from arclet.alconna import AllParam
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, UniMessage, on_alconna
from nonebot_plugin_user import User

from src.utils.helpers import render_expression

from .alisten_api import api

__plugin_meta__ = PluginMetadata(
    name="音乐",
    description="通过 alisten 服务点歌",
    usage="""参数为歌曲相关信息
/music Sagitta luminis               # 搜索并点歌
/点歌 青花瓷                          # 中文别名
/music BV1Xx411c7md                  # Bilibili BV号
/music qq:song_id                    # QQ音乐（需要指定来源）
/music wy:song_id                    # 网易云音乐（需要指定来源）

支持的音乐源：
- wy: 网易云音乐
- qq: QQ音乐
- db: Bilibili（支持BV号）
""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)


# 无法获取歌曲时的回答
EXPR_NOT_FOUND = (
    "为什么找不到匹配的歌呢！",
    "似乎哪里出错了，找不到你想点的歌 ~><~",
    "没有找到，要不要换个关键字试试？",
)

# 点歌成功的回答
EXPR_SUCCESS = (
    "点歌成功！歌曲已加入播放列表",
    "好的，已经为你点了这首歌！",
    "收到，歌曲已添加到队列中～",
)

music_cmd = on_alconna(
    Alconna(
        "music",
        Args["keywords?#音乐名称或信息", AllParam],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"点歌"},
    use_cmd_start=True,
    block=True,
)


@music_cmd.handle()
async def music_handle_first_receive(keywords: Match[UniMessage]):
    if keywords.available:
        music_cmd.set_path_arg("keywords", keywords.result)


@music_cmd.got_path("keywords", prompt="你想听哪首歌呢？")
async def music_handle(keywords: UniMessage, user: User):
    """处理点歌请求"""
    name = keywords.extract_plain_text().strip()
    source = "wy"  # 默认音乐源

    # 解析特殊格式的输入
    if ":" in name:
        # 格式如 "wy:song_id" 或 "qq:song_id"
        parts = name.split(":", 1)
        if len(parts) == 2 and parts[0] in ["wy", "qq", "db"]:
            source = parts[0]
            name = parts[1]
    elif name.startswith("BV"):
        # Bilibili BV号
        source = "db"

    result = await api.pick_music(name=name, user_name=user.name, source=source)

    if result.success:
        success_msg = render_expression(EXPR_SUCCESS)
        if result.name:
            success_msg += f"\n歌曲：{result.name}"
        if result.source:
            source_name = {
                "wy": "网易云音乐",
                "qq": "QQ音乐",
                "db": "Bilibili",
            }.get(result.source, result.source)
            success_msg += f"\n来源：{source_name}"
        await music_cmd.finish(success_msg, at_sender=True)
    else:
        await music_cmd.finish(f"点歌失败：{result.message}", at_sender=True)
