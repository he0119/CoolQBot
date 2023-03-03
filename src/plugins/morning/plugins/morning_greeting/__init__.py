""" 每日早安 """
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata, on_command
from nonebot_plugin_apscheduler import scheduler

from src.utils.helpers import strtobool

from ... import plugin_config
from .data_source import HOLIDAYS_DATA, get_moring_message

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
        "adapters": ["OneBot V11"],
    },
)


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


morning_cmd = on_command("morning", aliases={"早安"}, permission=GROUP, block=True)


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
