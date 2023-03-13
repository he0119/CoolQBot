""" 复读 """
from nonebot import on_message
from nonebot.adapters import Event, Message
from nonebot.params import CommandArg, Depends
from nonebot.plugin import PluginMetadata
from nonebot_plugin_datastore import get_session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.helpers import (
    GroupOrChannel,
    get_group_or_channel,
    get_platform,
    strtobool,
)

from ... import repeat
from ...models import Enabled
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
    extra={
        "adapters": ["OneBot V11", "OneBot V12"],
    },
)


repeat_message = on_message(rule=need_repeat, priority=50, block=True)


@repeat_message.handle()
async def repeat_message_handle(event: Event):
    await repeat_message.finish(event.get_message())


repeat_cmd = repeat.command("basic", aliases={"repeat", "复读"})
repeat_cmd.__doc__ = """
复读

查看当前群是否启用复读功能\n/repeat\n启用复读功能\n/repeat on\n关闭复读功能\n/repeat off
"""


@repeat_cmd.handle()
async def repeat_handle(
    arg: Message = CommandArg(),
    session: AsyncSession = Depends(get_session),
    group_or_channel: GroupOrChannel = Depends(get_group_or_channel),
    platform: str = Depends(get_platform),
):
    args = arg.extract_plain_text()

    group = (
        await session.scalars(
            select(Enabled)
            .where(Enabled.platform == platform)
            .where(Enabled.group_id == group_or_channel.group_id)
            .where(Enabled.guild_id == group_or_channel.guild_id)
            .where(Enabled.channel_id == group_or_channel.channel_id)
        )
    ).one_or_none()

    if args:
        if strtobool(args):
            if not group:
                session.add(
                    Enabled(platform=platform, **group_or_channel.group_or_channel_id)
                )
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
