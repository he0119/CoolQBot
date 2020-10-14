""" 每日早安插件
"""
from nonebot import get_bots, get_driver, logger, on_metaevent, scheduler
from nonebot.rule import Rule
from nonebot.typing import Bot, Event

from .config import Config
from .data import get_first_connect_message, get_moring_message

morning_config = Config(**get_driver().config.dict())


async def check_first_connect(bot: Bot, event: Event, state: dict) -> bool:
    if event.sub_type == 'connect':
        return True
    return False


morning = on_metaevent(priority=5, block=True, rule=Rule(check_first_connect))


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
    hour=morning_config.morning_hour,
    minute=morning_config.morning_minute,
    second=morning_config.morning_second,
    id='morning'
)
async def morning():
    """ 早安
    """
    hello_str = await get_moring_message()
    await list(get_bots().values())[0].send_msg(
        message_type='group',
        group_id=get_driver().config.group_id,
        message=hello_str
    )
    logger.info('发送早安信息')
