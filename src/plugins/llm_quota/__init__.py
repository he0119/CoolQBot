"""大模型额度查询插件

查询大模型剩余额度，详见 README.md。
"""

from nonebot import require
from nonebot.adapters import Bot, Event
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_alconna")
require("nonebot_plugin_orm")
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Subcommand, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_uninfo import get_session
from nonebot_plugin_user import UserSession

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
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "额度"}),
    ],
)


@quota_cmd.assign("set")
async def quota_set_handle(bot: Bot, event: Event, user: UserSession, api_url: str):
    session = await get_session(bot, event)
    if not session:
        await quota_cmd.finish("无法获取会话信息")
    from nonebot_plugin_user.utils import get_user

    user_obj = await get_user(session.scope, session.user.id)
    if user_obj.name not in bot.config.superusers:
        await quota_cmd.finish("仅管理员可使用此命令", at_sender=True)
    await set_group_api_url(user.session_id, api_url)
    await quota_cmd.finish(f"已设置额度查询 API 地址：{api_url}", at_sender=True)


@quota_cmd.assign("remove")
async def quota_remove_handle(bot: Bot, event: Event, user: UserSession):
    session = await get_session(bot, event)
    if not session:
        await quota_cmd.finish("无法获取会话信息")
    from nonebot_plugin_user.utils import get_user

    user_obj = await get_user(session.scope, session.user.id)
    if user_obj.name not in bot.config.superusers:
        await quota_cmd.finish("仅管理员可使用此命令", at_sender=True)
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
