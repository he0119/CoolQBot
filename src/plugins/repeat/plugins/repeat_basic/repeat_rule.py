""" 复读 """
import secrets
from datetime import datetime, timedelta

from nonebot.adapters import Event
from nonebot.log import logger
from nonebot.params import Depends

from src.utils.helpers import GroupInfo, get_group_info

from ... import plugin_config
from ...recorder import Recorder


async def need_repeat(
    event: Event,
    group_info: GroupInfo = Depends(get_group_info),
) -> bool:
    """是否复读这个消息"""
    # 不复读对机器人说的，因为这个应该由闲聊插件处理
    if event.is_tome():
        return False

    user_id = event.get_user_id()

    # 只复读指定群内消息
    recorder = Recorder(group_info)
    if not await recorder.is_enabled():
        return False

    # 不要复读指令
    if event.get_plaintext().startswith("/"):
        return False

    # 记录群内发送消息数量和时间
    now = datetime.now()
    recorder.add_msg_send_time(now)

    # 不要复读应用消息
    if user_id == 1000000:
        return False

    # 不要复读签到，分享，小程序，转发，红包
    if event.get_message()[0].type in ["sign", "share", "json", "forward", "redbag"]:
        return False

    # 不要复读带网址的消息
    if (
        "http://" in event.get_plaintext().lower()
        or "https://" in event.get_plaintext().lower()
    ):
        return False

    # 复读之后一定时间内不再复读
    time = recorder.last_message_on()
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
        # 只有判断过后的消息才会被记录
        await recorder.add_msg_number_list(user_id)
        return False

    await recorder.add_repeat_list(user_id)
    # 记录复读时间
    recorder.reset_last_message_on()

    return True
