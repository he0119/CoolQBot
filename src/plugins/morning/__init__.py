""" 每日早安插件
"""
import nonebot
from nonebot import get_bot, logger, require
from nonebot.adapters import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.plugin import on_command

from src.utils.helpers import strtobool

from .config import plugin_config
from .data import get_first_connect_message, get_moring_message

scheduler = require("nonebot_plugin_apscheduler").scheduler
driver = nonebot.get_driver()


#region 启动问好
@driver.on_bot_connect
async def hello_on_connect(bot: Bot) -> None:
    """ 启动时发送问好信息 """
    hello_str = get_first_connect_message()
    for group_id in plugin_config.group_id:
        await bot.send_msg(message_type='group',
                           group_id=group_id,
                           message=hello_str)
    logger.info('发送首次启动的问好信息')


#endregion
#region 每日早安
@scheduler.scheduled_job('cron',
                         hour=plugin_config.morning_hour,
                         minute=plugin_config.morning_minute,
                         second=plugin_config.morning_second,
                         id='morning')
async def morning():
    """ 早安 """
    hello_str = await get_moring_message()
    for group_id in plugin_config.group_id:
        await get_bot().send_msg(
            message_type='group',
            group_id=group_id,
            message=hello_str,
        )
    logger.info('发送早安信息')


morning_cmd = on_command('morning', aliases={'早安'}, permission=GROUP)
morning_cmd.__doc__ = """
morning 早安

每日早安

启用时会在每天早晨发送早安信息

查看当前群是否启用每日早安功能
/morning
启用每日早安功能
/morning on
关闭每日早安功能
/morning off
"""


@morning_cmd.handle()
async def morning_handle(bot: Bot, event: GroupMessageEvent):
    args = str(event.message).strip()

    group_id = event.group_id

    if args == 'test':
        await morning_cmd.finish(await get_moring_message())

    if args and group_id:
        if strtobool(args):
            plugin_config.group_id += [group_id]
            await morning_cmd.finish('已在本群开启每日早安功能')
        else:
            plugin_config.group_id = [
                n for n in plugin_config.group_id if n != group_id
            ]
            await morning_cmd.finish('已在本群关闭每日早安功能')
    else:
        if group_id in plugin_config.group_id:
            await morning_cmd.finish('每日早安功能开启中')
        else:
            await morning_cmd.finish('每日早安功能关闭中')


#endregion
