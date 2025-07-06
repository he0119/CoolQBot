"""每日早安"""

from nonebot.exception import ActionFailed
from nonebot.log import logger
from nonebot.params import Depends
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_orm import get_session
from nonebot_plugin_saa import PlatformTarget, Text, get_target
from sqlalchemy import select

from src.plugins.morning import plugin_config
from src.utils.annotated import AsyncSession
from src.utils.helpers import admin_permission, strtobool

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
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_saa"),
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
    async with get_session() as session:
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


morning_cmd = on_alconna(
    Alconna(
        "早安",
        Args["arg?#功能选项（on/off/update/today）", str],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"morning"},
    use_cmd_start=True,
    block=True,
    permission=admin_permission(),
)


@morning_cmd.handle()
async def morning_handle(session: AsyncSession, arg: Match[str], target: PlatformTarget = Depends(get_target)):
    if arg.available:
        if arg.result == "today":
            await morning_cmd.finish(await get_moring_message())

        if arg.result == "update":
            await HOLIDAYS_DATA.update()
            await morning_cmd.finish("节假日数据更新成功")

    group = (
        await session.scalars(select(MorningGreeting).where(MorningGreeting.target == target.model_dump()))
    ).one_or_none()
    if arg.available:
        if strtobool(arg.result):
            if not group:
                session.add(MorningGreeting(target=target.model_dump()))
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
