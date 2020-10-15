""" 复读插件

按照一定条件复读聊天
拥有一些配套功能，如复读排行榜，排行榜历史记录，复读状态
"""
from nonebot import get_driver, on_command, on_message, scheduler
from nonebot.permission import GROUP
from nonebot.rule import Rule
from nonebot.typing import Bot, Event

from .recorder import recorder
from .repeat_rule import is_repeat
from .status import get_status


#region 自动保存数据
@scheduler.scheduled_job('interval', minutes=1, id='save_recorder')
async def save_recorder():
    """ 每隔一分钟保存一次数据
    """
    # 保存数据前先清理 msg_send_time 列表，仅保留最近 10 分钟的数据
    for group_id in get_driver().config.group_id:
        recorder.message_number(10, group_id)

    recorder.save_data()


#endregion
#region 复读
repeat_basic = on_message(
    rule=Rule(is_repeat),
    permission=GROUP,
    priority=5,
    block=True,
)


@repeat_basic.handle()
async def handle_repeat(bot: Bot, event: Event, state: dict):
    await repeat_basic.finish(event.raw_message)


#endregion
#region 运行状态
repeat_status = on_command(
    'status',
    aliases=['状态'],
    priority=5,
    block=True,
)


@repeat_status.handle()
async def handle_status(bot: Bot, event: Event, state: dict):
    await repeat_status.finish(get_status(event.group_id))


#endregion
