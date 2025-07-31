"""复读"""

from nonebot import on_message
from nonebot.adapters import Event
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from sqlalchemy import select

from src.plugins.repeat.models import Enabled
from src.utils.annotated import AsyncSession, GroupInfo
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
    supported_adapters={"~onebot.v11", "~onebot.v12"},
)


repeat_message = on_message(rule=need_repeat, priority=50, block=True)


@repeat_message.handle()
async def repeat_message_handle(event: Event):
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
)


@repeat_cmd.handle()
async def repeat_handle(session: AsyncSession, group_info: GroupInfo, arg: Match[str]):
    group = (
        await session.scalars(
            select(Enabled)
            .where(Enabled.platform == group_info.platform)
            .where(Enabled.group_id == group_info.group_id)
            .where(Enabled.guild_id == group_info.guild_id)
            .where(Enabled.channel_id == group_info.channel_id)
        )
    ).one_or_none()

    if arg.available:
        if strtobool(arg.result):
            if not group:
                session.add(Enabled(**group_info.model_dump()))
                await session.commit()
            await repeat_cmd.finish("已在本群开启复读功能")
        else:
            if group:
                await session.delete(group)
                await session.commit()
            await repeat_cmd.finish("已在本群关闭复读功能")
    else:
        if group:
            await repeat_cmd.finish("复读功能开启中")
        else:
            await repeat_cmd.finish("复读功能关闭中")
