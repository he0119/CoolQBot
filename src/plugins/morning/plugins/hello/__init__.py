""" 启动问候 """
import nonebot
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot as V11Bot
from nonebot.adapters.onebot.v12 import Bot as V12Bot
from nonebot.adapters.onebot.v12 import Message as V12Message
from nonebot.exception import ActionFailed
from nonebot.log import logger
from nonebot.params import CommandArg, Depends
from nonebot.plugin import PluginMetadata, on_command
from nonebot_plugin_datastore import create_session, get_session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.helpers import (
    GroupOrChannel,
    get_group_or_channel,
    get_platform,
    strtobool,
)

from .data_source import get_first_connect_message
from .models import Hello

__plugin_meta__ = PluginMetadata(
    name="启动问候",
    description="启动时发送问候",
    usage="""开启时会在每天机器人第一次启动时发送问候

查看当前群是否开启启动问候
/hello
开启启动问候功能
/hello on
关闭启动问候功能
/hello off""",
    extra={
        "adapters": ["OneBot V11", "OneBot V12"],
    },
)

driver = nonebot.get_driver()


@driver.on_bot_connect
async def hello_on_connect(
    bot: V11Bot | V12Bot,
    platform: str = Depends(get_platform),
) -> None:
    """启动时发送问候"""
    async with create_session() as session:
        groups = (
            await session.scalars(select(Hello).where(Hello.platform == platform))
        ).all()
    if not groups:
        return

    hello_str = get_first_connect_message()
    for group in groups:
        try:
            if isinstance(bot, V11Bot):
                await bot.send_group_msg(
                    message=hello_str, group_id=int(group.group_id)
                )
            else:
                await bot.send_message(
                    detail_type="group" if group.group_id else "channel",
                    message=V12Message(hello_str),
                    group_id=group.group_id,
                    guild_id=group.guild_id,
                    channel_id=group.channel_id,
                )
        except ActionFailed as e:
            logger.error(f"发送启动问候失败: {e}")
    logger.info("发送首次启动的问候")


hello_cmd = on_command("hello", aliases={"问候"}, block=True)


@hello_cmd.handle()
async def hello_handle(
    arg: Message = CommandArg(),
    session: AsyncSession = Depends(get_session),
    platform: str = Depends(get_platform),
    group_or_channel: GroupOrChannel = Depends(get_group_or_channel),
):
    args = arg.extract_plain_text()

    group = (
        await session.scalars(
            select(Hello)
            .where(Hello.platform == platform)
            .where(Hello.group_id == group_or_channel.group_id)
            .where(Hello.guild_id == group_or_channel.guild_id)
            .where(Hello.channel_id == group_or_channel.channel_id)
        )
    ).one_or_none()

    if args:
        if strtobool(args):
            if not group:
                session.add(
                    Hello(platform=platform, **group_or_channel.group_or_channel_id),
                )
                await session.commit()
            await hello_cmd.finish("已在本群开启启动问候功能")
        else:
            if group:
                await session.delete(group)
                await session.commit()
            await hello_cmd.finish("已在本群关闭启动问候功能")
    else:
        if group:
            await hello_cmd.finish("启动问候功能开启中")
        else:
            await hello_cmd.finish("启动问候功能关闭中")
