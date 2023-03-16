""" 每日早安 """
from dataclasses import asdict

from nonebot import get_bot
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot as V11Bot
from nonebot.adapters.onebot.v12 import Bot as V12Bot
from nonebot.adapters.onebot.v12 import Message as V12Message
from nonebot.log import logger
from nonebot.params import CommandArg, Depends
from nonebot.plugin import PluginMetadata, on_command
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_datastore import create_session, get_session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.helpers import GroupInfo, get_group_info, strtobool

from ... import plugin_config
from .data_source import HOLIDAYS_DATA, get_moring_message
from .models import MorningGreeting

__plugin_meta__ = PluginMetadata(
    name="每日早安",
    description="早上好，什么时候放假呢？",
    usage="""开启时会在每天早晨发送早安信息

查看当前群是否开启每日早安功能
/morning
开启每日早安功能
/morning on
关闭每日早安功能
/morning off
更新节假日数据
/morning update
获取今天的问好
/morning today""",
    extra={
        "adapters": ["OneBot V11", "OneBot V12"],
    },
)


@scheduler.scheduled_job(
    "cron",
    hour=plugin_config.morning_time.hour,
    minute=plugin_config.morning_time.minute,
    second=plugin_config.morning_time.second,
    id="morning",
)
async def morning():
    """早安"""
    async with create_session() as session:
        groups = (await session.scalars(select(MorningGreeting))).all()

    if not groups:
        return

    hello_str = await get_moring_message()
    for group in groups:
        try:
            bot = get_bot(group.bot_id)
        except ValueError:
            logger.warning(f"Bot {group.bot_id} 不存在，跳过")
            continue
        group_info = GroupInfo.parse_obj(asdict(group))
        if isinstance(bot, V11Bot):
            await get_bot().send_msg(
                message_type="group",
                group_id=group_info.group_id,
                message=hello_str,
            )
        elif isinstance(bot, V12Bot):
            await bot.send_message(
                detail_type=group_info.detail_type,
                message=V12Message(hello_str),
                **group_info.send_message_args,
            )
    logger.info("发送早安信息")


morning_cmd = on_command("morning", aliases={"早安"}, block=True)


@morning_cmd.handle()
async def morning_handle(
    bot: V11Bot | V12Bot,
    arg: Message = CommandArg(),
    session: AsyncSession = Depends(get_session),
    group_info: GroupInfo = Depends(get_group_info),
):
    args = arg.extract_plain_text()

    if args == "today":
        await morning_cmd.finish(await get_moring_message())

    if args == "update":
        await HOLIDAYS_DATA.update()
        await morning_cmd.finish("节假日数据更新成功")

    group = (
        await session.scalars(
            select(MorningGreeting)
            .where(MorningGreeting.bot_id == bot.self_id)
            .where(MorningGreeting.platform == group_info.platform)
            .where(MorningGreeting.group_id == group_info.group_id)
            .where(MorningGreeting.guild_id == group_info.guild_id)
            .where(MorningGreeting.channel_id == group_info.channel_id)
        )
    ).one_or_none()
    if args:
        if strtobool(args):
            if not group:
                session.add(MorningGreeting(bot_id=bot.self_id, **group_info.dict()))
                await session.commit()
            await morning_cmd.finish("已在本群开启每日早安功能")
        else:
            if group:
                await session.delete(group)
                await session.commit()
            await morning_cmd.finish("已在本群关闭每日早安功能")
    else:
        if group:
            await morning_cmd.finish("每日早安功能开启中")
        else:
            await morning_cmd.finish("每日早安功能关闭中")
