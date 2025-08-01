"""时尚品鉴"""

from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, CommandMeta, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension

from .data_source import get_latest_nuannuan

__plugin_meta__ = PluginMetadata(
    name="时尚品鉴",
    description="获取最新的满分攻略",
    usage="""获取最新的满分攻略
/时尚品鉴""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)

nuannuan_cmd = on_alconna(
    Alconna(
        "nuannuan",
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"时尚品鉴"},
    use_cmd_start=True,
    block=True,
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "时尚品鉴"}),
    ],
)


@nuannuan_cmd.handle()
async def nuannuan_handle():
    """时尚品鉴"""
    latest = await get_latest_nuannuan()
    if latest:
        await nuannuan_cmd.finish(latest)
    else:
        await nuannuan_cmd.finish("抱歉，没有找到最新的满分攻略。")
