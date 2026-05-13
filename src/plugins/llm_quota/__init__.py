"""大模型额度查询插件

查询大模型剩余额度，详见 README.md。
"""

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import Alconna, CommandMeta, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension

from .data_source import get_quotas

__plugin_meta__ = PluginMetadata(
    name="大模型额度",
    description="查询大模型剩余额度",
    usage="/quota 或 /额度",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)

quota_cmd = on_alconna(
    Alconna(
        "quota",
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"额度"},
    use_cmd_start=True,
    block=True,
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "额度"}),
    ],
)


@quota_cmd.handle()
async def quota_handle():
    result = await get_quotas()
    await quota_cmd.finish(result)
