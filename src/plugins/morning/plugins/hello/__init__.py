""" 启动问候 """
from nonebot import require

require("nonebot_plugin_saa")
import nonebot
from nonebot.adapters import Bot, Message
from nonebot.exception import ActionFailed
from nonebot.log import logger
from nonebot.params import CommandArg, Depends
from nonebot.plugin import PluginMetadata, inherit_supported_adapters, on_command
from nonebot_plugin_saa import PlatformTarget, Text, get_target
from sqlalchemy import select

from src.utils.annotated import AsyncSession
from src.utils.helpers import strtobool

from . import migrations
from .data_source import get_first_connect_message
from .models import Hello

__plugin_meta__ = PluginMetadata(
    name="启动问候",
    description="启动时发送问候",
    usage="""开启时会在机器人第一次启动时发送问候

查看当前群是否开启启动问候
/hello
开启启动问候功能
/hello on
关闭启动问候功能
/hello off""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_saa"),
    extra={"orm_version_location": migrations},
)

driver = nonebot.get_driver()


@driver.on_bot_connect
async def hello_on_connect(bot: Bot, session: AsyncSession) -> None:
    """启动时发送问候"""
    groups = (
        await session.scalars(select(Hello).where(Hello.bot_id == bot.self_id))
    ).all()
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
    bot: Bot,
    session: AsyncSession,
    arg: Message = CommandArg(),
    target: PlatformTarget = Depends(get_target),
):
    args = arg.extract_plain_text()

    group = (
        await session.scalars(
            select(Hello)
            .where(Hello.target == target.model_dump())
            .where(Hello.bot_id == bot.self_id)
        )
    ).one_or_none()

    if args:
        if strtobool(args):
            if not group:
                session.add(Hello(target=target.model_dump(), bot_id=bot.self_id))
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
