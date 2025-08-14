"""壁画插件"""

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.rule import Rule

require("nonebot_plugin_orm")
require("nonebot_plugin_user")
require("nonebot_plugin_alconna")
require("nonebot_plugin_localstore")
require("src.utils.group_bind")
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaMatch,
    AlconnaMatcher,
    Args,
    CommandMeta,
    Image,
    Match,
    Option,
    UniMessage,
    image_fetch,
    on_alconna,
    store_true,
)
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.reply import ReplyMergeExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession, get_user_by_id

from src.utils.helpers import admin_permission

from .data_source import BihuaService

__plugin_meta__ = PluginMetadata(
    name="壁画收藏",
    description="收藏、查看和搜索壁画",
    usage="""收藏壁画（回复图片）
/收藏壁画 壁画名称
查看壁画
/壁画 壁画名称
搜索壁画
/搜索壁画 关键词
删除壁画
/删除壁画 壁画名称""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)

bihua_service = BihuaService()


async def is_group(session: UserSession) -> bool:
    """确保在群组中使用"""
    return not session.session.scene.is_private


# 收藏壁画命令
post_cmd = on_alconna(
    Alconna(
        "post",
        Args["name#名称", str]["img?#图片", Image],
        meta=CommandMeta(
            description="收藏壁画",
            example="发送图片和命令\n回复图片并发送 /收藏壁画 我从来不说壁画",
        ),
    ),
    aliases={"收藏壁画", "壁画收藏"},
    use_cmd_start=True,
    block=True,
    extensions=[
        ReplyMergeExtension(),
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "收藏壁画"}),
    ],
    rule=Rule(is_group),
)


@post_cmd.handle()
async def _(
    matcher: AlconnaMatcher,
    img: Match[bytes] = AlconnaMatch("img", image_fetch),
):
    if img.available:
        matcher.set_path_arg("img", img.result)


@post_cmd.got_path("img", "请发送需要收藏的壁画", image_fetch)
async def handle_save_bihua(user: UserSession, name: str, img: bytes):
    try:
        # 保存壁画
        await bihua_service.add_bihua(user_id=user.user_id, session_id=user.session_id, name=name, image_data=img)
        await post_cmd.finish(f"壁画 '{name}' 收藏成功！")

    except ValueError as e:
        await post_cmd.finish(f"收藏失败：{e}")


# 查看壁画命令
bihua_cmd = on_alconna(
    Alconna(
        "bihua",
        Args["name", str],
        Option(
            "-v|--verbose",
            default=False,
            action=store_true,
            help_text="显示壁画详细信息",
        ),
        Option(
            "-e|--exact",
            default=False,
            action=store_true,
            help_text="精确匹配壁画名称",
        ),
        meta=CommandMeta(
            description="查看壁画",
            example="查看壁画\n/壁画 我从来不说壁画",
        ),
    ),
    use_cmd_start=True,
    block=True,
    aliases={"壁画"},
    rule=Rule(is_group),
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "壁画"}),
    ],
)


@bihua_cmd.handle()
async def _(user: UserSession, name: str, verbose: bool = False, exact: bool = False):
    """查看壁画"""
    if exact:
        bihua = await bihua_service.get_bihua_by_name(name, user.session_id)
    else:
        bihua_list = await bihua_service.search_bihua(name, user.session_id)
        if not bihua_list:
            await bihua_cmd.finish(f"未找到壁画 '{name}'")
        # 取第一个匹配的壁画
        bihua = bihua_list[0]

    if not bihua:
        await bihua_cmd.finish(f"未找到壁画 '{name}'")

    # 构建响应消息
    msg = UniMessage()
    if verbose:
        # 获取收藏者信息
        collector = await get_user_by_id(bihua.user_id)
        msg += f"壁画：{bihua.name}\n"
        msg += f"收藏者：{collector.name}\n"
        msg += f"收藏时间：{bihua.created_at:%Y-%m-%d %H:%M}\n"

    # 发送图片
    image_path = bihua.image_path()
    if image_path.exists():
        with open(image_path, "rb") as f:
            image_data = f.read()
        msg += Image(raw=image_data)
    else:
        msg += "图片文件不存在"

    await bihua_cmd.finish(msg)


# 搜索壁画命令
bihua_search_cmd = on_alconna(
    Alconna(
        "bihua_search",
        Args["keyword", str],
        meta=CommandMeta(
            description="搜索壁画",
            example="搜索壁画\n/搜索壁画 关键词",
        ),
    ),
    aliases={"壁画搜索", "搜索壁画"},
    use_cmd_start=True,
    block=True,
    rule=Rule(is_group),
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "搜索壁画"}),
    ],
)


@bihua_search_cmd.handle()
async def _(user: UserSession, keyword: str):
    bihua_list = await bihua_service.search_bihua(keyword, user.session_id)

    if not bihua_list:
        await bihua_search_cmd.finish(f"未找到包含 '{keyword}' 的壁画")

    # 构建结果列表
    result_lines = [f"搜索到 {len(bihua_list)} 个相关壁画："]
    for bihua in bihua_list:
        collector = await get_user_by_id(bihua.user_id)
        result_lines.append(f"• {bihua.name} (收藏者: {collector.name})")

    await bihua_search_cmd.finish("\n".join(result_lines))


# 删除壁画命令
bihua_delete_cmd = on_alconna(
    Alconna(
        "bihua_delete",
        Args["name", str],
        meta=CommandMeta(
            description="删除壁画（仅管理员）",
            example="删除壁画\n/删除壁画 我从来不说壁画",
        ),
    ),
    aliases={"删除壁画", "壁画删除"},
    permission=admin_permission(),
    use_cmd_start=True,
    block=True,
    rule=Rule(is_group),
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "删除壁画"}),
    ],
)


@bihua_delete_cmd.handle()
async def _(user: UserSession, name: str):
    try:
        await bihua_service.delete_bihua(name, user.session_id)
        await bihua_delete_cmd.finish(f"壁画 '{name}' 删除成功！")
    except ValueError as e:
        await bihua_delete_cmd.finish(f"删除失败：{e}")
