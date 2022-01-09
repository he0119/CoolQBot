""" 每日早安插件
"""
import nonebot
from nonebot import get_bot, require
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import Message
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.plugin import on_command

from src.utils.helpers import strtobool

from .config import plugin_config
from .data import HOLIDAYS_DATA, get_first_connect_message, get_moring_message

scheduler = require("nonebot_plugin_apscheduler").scheduler
driver = nonebot.get_driver()


# region 启动问候
@driver.on_bot_connect
async def hello_on_connect(bot: Bot) -> None:
    """启动时发送问候"""
    hello_str = get_first_connect_message()
    for group_id in plugin_config.hello_group_id:
        await bot.send_msg(message_type="group", group_id=group_id, message=hello_str)
    logger.info("发送首次启动的问候")


hello_cmd = on_command("hello", aliases={"问候"}, permission=GROUP)
hello_cmd.__doc__ = """
启动问候

开启时会在每天机器人第一次启动时发送问候

查看当前群是否开启启动问候
/hello
开启启动问候功能
/hello on
关闭启动问候功能
/hello off
"""


@hello_cmd.handle()
async def hello_handle(event: GroupMessageEvent, arg: Message = CommandArg()):
    args = arg.extract_plain_text()

    group_id = event.group_id

    if args and group_id:
        if strtobool(args):
            plugin_config.hello_group_id += [group_id]
            await hello_cmd.finish("已在本群开启启动问候功能")
        else:
            plugin_config.hello_group_id = [
                n for n in plugin_config.hello_group_id if n != group_id
            ]
            await hello_cmd.finish("已在本群关闭启动问候功能")
    else:
        if group_id in plugin_config.hello_group_id:
            await hello_cmd.finish("启动问候功能开启中")
        else:
            await hello_cmd.finish("启动问候功能关闭中")


# endregion
# region 每日早安
@scheduler.scheduled_job(
    "cron",
    hour=plugin_config.morning_hour,
    minute=plugin_config.morning_minute,
    second=plugin_config.morning_second,
    id="morning",
)
async def morning():
    """早安"""
    hello_str = await get_moring_message()
    for group_id in plugin_config.morning_group_id:
        await get_bot().send_msg(
            message_type="group",
            group_id=group_id,
            message=hello_str,
        )
    logger.info("发送早安信息")


morning_cmd = on_command("morning", aliases={"早安"}, permission=GROUP)
morning_cmd.__doc__ = """
每日早安

开启时会在每天早晨发送早安信息

查看当前群是否开启每日早安功能
/morning
开启每日早安功能
/morning on
关闭每日早安功能
/morning off
更新节假日数据
/morning update
获取今天的问好
/morning today
"""


@morning_cmd.handle()
async def morning_handle(event: GroupMessageEvent, arg: Message = CommandArg()):
    args = arg.extract_plain_text()

    group_id = event.group_id

    if args == "today":
        await morning_cmd.finish(await get_moring_message())

    if args == "update":
        await HOLIDAYS_DATA.update()
        await morning_cmd.finish("节假日数据更新成功")

    if args and group_id:
        if strtobool(args):
            plugin_config.morning_group_id += [group_id]
            await morning_cmd.finish("已在本群开启每日早安功能")
        else:
            plugin_config.morning_group_id = [
                n for n in plugin_config.morning_group_id if n != group_id
            ]
            await morning_cmd.finish("已在本群关闭每日早安功能")
    else:
        if group_id in plugin_config.morning_group_id:
            await morning_cmd.finish("每日早安功能开启中")
        else:
            await morning_cmd.finish("每日早安功能关闭中")


# endregion
