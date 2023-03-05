""" 复读 """
import secrets
from datetime import datetime, timedelta

from nonebot.adapters import Event
from nonebot.log import logger
from nonebot.params import Depends, EventToMe
from nonebot_plugin_datastore import get_session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.helpers import GroupOrChannel, get_group_or_channel, get_platform

from ... import plugin_config, recorder_obj
from ...models import Enabled


async def need_repeat(
    event: Event,
    to_me: bool = EventToMe(),
    session: AsyncSession = Depends(get_session),
    group_or_channel: GroupOrChannel = Depends(get_group_or_channel),
    platform: str = Depends(get_platform),
) -> bool:
    """是否复读这个消息"""
    # 不复读对机器人说的，因为这个应该由闲聊插件处理
    if to_me:
        return False

    user_id = event.get_user_id()

    # 只复读指定群内消息
    group = (
        await session.scalars(
            select(Enabled)
            .where(Enabled.platform == platform)
            .where(Enabled.group_id == group_or_channel.group_id)
            .where(Enabled.guild_id == group_or_channel.guild_id)
            .where(Enabled.channel_id == group_or_channel.channel_id)
        )
    ).one_or_none()
    if not group:
        return False

    # 不要复读指令
    if event.get_plaintext().startswith("/"):
        return False

    # 记录群内发送消息数量和时间
    now = datetime.now()
    recorder_obj.add_msg_send_time(now, platform, **group_or_channel.dict())

    # 不要复读应用消息
    if user_id == 1000000:
        return False

    # 不要复读签到，分享，小程序，转发
    if event.get_message()[0].type in ["sign", "share", "json", "forward"]:
        return False

    # 不要复读带网址的消息
    if (
        "http://" in event.get_plaintext().lower()
        or "https://" in event.get_plaintext().lower()
    ):
        return False

    # 复读之后一定时间内不再复读
    time = recorder_obj.last_message_on(platform, **group_or_channel.dict())
    if time is not None and now < time + timedelta(
        minutes=plugin_config.repeat_interval
    ):
        return False

    repeat_rate = plugin_config.repeat_rate
    # 当10分钟内发送消息数量大于30条时，降低复读概率
    # 因为排行榜需要固定概率来展示欧非，暂时取消
    # if recorder.message_number(10) > 30:
    #     logger.info('Repeat rate changed!')
    #     repeat_rate = 5

    # 按照设定概率复读
    random = secrets.SystemRandom()
    rand = random.randint(1, 100)
    logger.info(f"repeat: {rand}")
    if rand > repeat_rate:
        await recorder_obj.add_msg_number_list(
            platform, user_id, **group_or_channel.dict()
        )
        return False

    # 记录复读时间
    recorder_obj.reset_last_message_on(platform, **group_or_channel.dict())

    await recorder_obj.add_repeat_list(platform, user_id, **group_or_channel.dict())

    return True
