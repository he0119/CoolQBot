""" 每日早安插件
"""
from nonebot import logger, on_metaevent, scheduler
from nonebot.permission import GROUP
from nonebot.plugin import on_command
from nonebot.typing import Bot, Event

from src.utils.helpers import get_first_bot, strtobool

from .config import plugin_config
from .data import get_first_connect_message, get_moring_message


#region 启动问好
def check_first_connect(bot: Bot, event: Event, state: dict) -> bool:
    if event.sub_type == 'connect':
        return True
    return False


morning_metaevent = on_metaevent(rule=check_first_connect, block=True)


@morning_metaevent.handle()
async def _(bot: Bot, event: Event, state: dict):
    """ 启动时发送问好信息 """
    hello_str = get_first_connect_message()
    for group_id in bot.config.group_id:
        await bot.send_msg(
            message_type='group', group_id=group_id, message=hello_str
        )
    logger.info('发送首次启动的问好信息')


#endregion
#region 每日早安
@scheduler.scheduled_job(
    'cron',
    hour=plugin_config.morning_hour,
    minute=plugin_config.morning_minute,
    second=plugin_config.morning_second,
    id='morning'
)
async def _():
    """ 早安 """
    hello_str = await get_moring_message()
    for group_id in plugin_config.group_id:
        await get_first_bot().send_msg(
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
async def _(bot: Bot, event: Event, state: dict):
    args = str(event.message).strip()

    group_id = event.group_id

    if args and group_id:
        if strtobool(args):
            plugin_config.group_id += [group_id]
            await morning_cmd.finish('已在本群开启每日早安功能')
        else:
            plugin_config.repeat_group_id = [
                n for n in plugin_config.group_id if n != group_id
            ]
            await morning_cmd.finish('已在本群关闭每日早安功能')
    else:
        if group_id in plugin_config.group_id:
            await morning_cmd.finish('每日早安功能开启中')
        else:
            await morning_cmd.finish('每日早安功能关闭中')


#endregion
