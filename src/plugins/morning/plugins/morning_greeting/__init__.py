""" 每日早安 """
from nonebot.adapters import Message
from nonebot.exception import ActionFailed
from nonebot.log import logger
from nonebot.params import CommandArg, Depends
from nonebot.plugin import PluginMetadata, inherit_supported_adapters, on_command
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_datastore import create_session
from nonebot_plugin_saa import PlatformTarget, Text, get_target
from sqlalchemy import select

from src.utils.annotated import AsyncSession
from src.utils.helpers import strtobool

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
    supported_adapters=inherit_supported_adapters("nonebot_plugin_saa"),
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
    msg = Text(hello_str)
    for group in groups:
        try:
            await msg.send_to(group.saa_target)
        except ActionFailed as e:
            logger.error(f"发送早安信息失败: {e}")

    logger.info("发送早安信息")


morning_cmd = on_command("morning", aliases={"早安"}, block=True)


@morning_cmd.handle()
async def morning_handle(
    session: AsyncSession,
    arg: Message = CommandArg(),
    target: PlatformTarget = Depends(get_target),
):
    args = arg.extract_plain_text()

    if args == "today":
        await morning_cmd.finish(await get_moring_message())

    if args == "update":
        await HOLIDAYS_DATA.update()
        await morning_cmd.finish("节假日数据更新成功")

    group = (
        await session.scalars(
            select(MorningGreeting).where(MorningGreeting.target == target.dict())
        )
    ).one_or_none()
    if args:
        if strtobool(args):
            if not group:
                session.add(MorningGreeting(target=target.dict()))
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
