"""大模型额度查询插件

查询大模型剩余额度，详见 README.md。
"""

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_alconna")
require("nonebot_plugin_orm")
require("nonebot_plugin_user")
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Subcommand, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession

from src.utils.helpers import admin_permission

from .data_source import get_group_api_url, get_quotas, remove_group_api_url, set_group_api_url

__plugin_meta__ = PluginMetadata(
    name="大模型额度",
    description="查询大模型剩余额度",
    usage="/quota 或 /额度",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)

quota_cmd = on_alconna(
    Alconna(
        "quota",
        Subcommand("set", Args["api_url#API 地址", str]),
        Subcommand("remove"),
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"额度"},
    use_cmd_start=True,
    block=True,
    permission=admin_permission(),
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "额度"}),
    ],
)


@quota_cmd.assign("set")
async def quota_set_handle(user: UserSession, api_url: str):
    await set_group_api_url(user.session_id, api_url)
    await quota_cmd.finish(f"已设置额度查询 API 地址：{api_url}", at_sender=True)


@quota_cmd.assign("remove")
async def quota_remove_handle(user: UserSession):
    removed = await remove_group_api_url(user.session_id)
    if removed:
        await quota_cmd.finish("已删除额度查询 API 配置", at_sender=True)
    else:
        await quota_cmd.finish("当前群组未配置额度查询 API", at_sender=True)


@quota_cmd.handle()
async def quota_handle(user: UserSession):
    api_url = await get_group_api_url(user.session_id)
    if not api_url:
        await quota_cmd.finish(
            "当前群组未配置额度查询 API，请管理员使用 /quota set 命令配置",
            at_sender=True,
        )
    result = await get_quotas(api_url)
    await quota_cmd.finish(result, at_sender=True)
