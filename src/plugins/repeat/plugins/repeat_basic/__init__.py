"""复读"""

from nonebot import on_message
from nonebot.adapters import Event
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession

from src.plugins.repeat.recorder import get_recorder
from src.utils.annotated import AsyncSession
from src.utils.helpers import strtobool

from .repeat_rule import need_repeat

__plugin_meta__ = PluginMetadata(
    name="复读功能",
    description="查看与设置复读功能",
    usage="""查看当前群是否启用复读功能
/repeat
启用复读功能
/repeat on
关闭复读功能
/repeat off""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)


repeat_message = on_message(rule=need_repeat, priority=50, block=True)


@repeat_message.handle()
async def repeat_message_handle(event: Event) -> None:
    await repeat_message.finish(event.get_message())


repeat_cmd = on_alconna(
    Alconna(
        "repeat",
        Args["arg?#是否启用复读", str],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"复读"},
    use_cmd_start=True,
    block=True,
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "复读"}),
    ],
)


@repeat_cmd.handle()
async def repeat_handle(session: AsyncSession, arg: Match[str], user: UserSession) -> None:
    recorder = get_recorder(user.session_id)

    if arg.available:
        if strtobool(arg.result):
            if not await recorder.is_enabled():
                await recorder.enable(session)
            await repeat_cmd.finish("已在本群开启复读功能")
        else:
            if await recorder.is_enabled():
                await recorder.disable(session)
            await repeat_cmd.finish("已在本群关闭复读功能")
    else:
        if await recorder.is_enabled():
            await repeat_cmd.finish("复读功能开启中")
        else:
            await repeat_cmd.finish("复读功能关闭中")
