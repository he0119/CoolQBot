""" 每日早安插件
"""
from nonebot import logger, on_metaevent, scheduler
from nonebot.typing import Bot, Event

from src.utils.helpers import get_first_bot

from .config import config
from .data import get_first_connect_message, get_moring_message


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


@scheduler.scheduled_job(
    'cron',
    hour=config.morning_hour,
    minute=config.morning_minute,
    second=config.morning_second,
    id='morning'
)
async def _():
    """ 早安
    """
    hello_str = await get_moring_message()
    for group_id in config.group_id:
        await get_first_bot().send_msg(
            message_type='group',
            group_id=group_id,
            message=hello_str,
        )
    logger.info('发送早安信息')
