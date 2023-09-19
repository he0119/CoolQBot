""" 启动问候 """
import nonebot
from nonebot.adapters import Bot, Message
from nonebot.exception import ActionFailed
from nonebot.log import logger
from nonebot.params import CommandArg, Depends
from nonebot.plugin import PluginMetadata, inherit_supported_adapters, on_command
from nonebot_plugin_saa import PlatformTarget, Text, get_target
from nonebot_plugin_saa.utils.auto_select_bot import (
    extract_adapter_type,
    list_targets_map,
)
from sqlalchemy import or_, select
from sqlalchemy.sql import ColumnElement

from src.utils.annotated import AsyncSession
from src.utils.helpers import strtobool

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
    supported_adapters=inherit_supported_adapters("nonebot_plugin_saa"),
)

driver = nonebot.get_driver()


@driver.on_bot_connect
async def hello_on_connect(bot: Bot, session: AsyncSession) -> None:
    """启动时发送问候"""
    whereclause: list[ColumnElement[bool]] = []
    adapter_name = extract_adapter_type(bot)
    if list_targets := list_targets_map.get(adapter_name):
        targets = await list_targets(bot)
        for target in targets:
            whereclause.append(or_(Hello.target == target.dict()))
    else:
        logger.info(f"不支持的适配器 {adapter_name}")
        return

    groups = (await session.scalars(select(Hello).where(*whereclause))).all()
    if not groups:
        return

    hello_str = get_first_connect_message()
    msg = Text(hello_str)
    for group in groups:
        try:
            await msg.send_to(group.saa_target, bot=bot)
        except ActionFailed as e:
            logger.error(f"发送启动问候失败: {e}")
    logger.info("发送首次启动的问候")


hello_cmd = on_command("hello", aliases={"问候"}, block=True)


@hello_cmd.handle()
async def hello_handle(
    session: AsyncSession,
    arg: Message = CommandArg(),
    target: PlatformTarget = Depends(get_target),
):
    args = arg.extract_plain_text()

    group = (
        await session.scalars(select(Hello).where(Hello.target == target.dict()))
    ).one_or_none()

    if args:
        if strtobool(args):
            if not group:
                session.add(Hello(target=target.dict()))
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
