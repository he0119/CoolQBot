""" 复读插件

按照一定条件复读聊天
拥有一些配套功能，如复读排行榜，排行榜历史记录，复读状态
"""
from nonebot import get_driver, on_message, scheduler
from nonebot.permission import GROUP
from nonebot.rule import Rule
from nonebot.typing import Bot, Event

from .recorder import recorder
from .repeat_rule import is_repeat


@scheduler.scheduled_job('interval', minutes=1, id='save_recorder')
async def save_recorder():
    """ 每隔一分钟保存一次数据
    """
    # 保存数据前先清理 msg_send_time 列表，仅保留最近 10 分钟的数据
    for group_id in get_driver().config.group_id:
        recorder.message_number(10, group_id)

    recorder.save_data()


# 复读
repeat = on_message(
    rule=Rule(is_repeat), permission=GROUP, priority=5, block=True
)


@repeat.handle()
async def handle_repeat(bot: Bot, event: Event, state: dict):
    await repeat.finish(event.raw_message)
