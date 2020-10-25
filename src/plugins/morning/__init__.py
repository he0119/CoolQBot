""" 每日早安插件
"""
from nonebot import logger, on_metaevent, scheduler
from nonebot.rule import Rule
from nonebot.typing import Bot, Event

from src.utils.helpers import get_first_bot

from .config import config
from .data import get_first_connect_message, get_moring_message


async def check_first_connect(bot: Bot, event: Event, state: dict) -> bool:
    if event.sub_type == 'connect':
        return True
    return False


morning = on_metaevent(
    rule=Rule(check_first_connect),
    priority=1,
    block=True,
)


@morning.handle()
async def handle_first_connect(bot: Bot, event: Event, state: dict):
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
async def morning():
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
