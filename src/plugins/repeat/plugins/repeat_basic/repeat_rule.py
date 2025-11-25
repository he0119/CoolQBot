"""复读"""

import secrets
from datetime import datetime, timedelta

from nonebot.adapters import Event
from nonebot.log import logger
from nonebot_plugin_user import UserSession

from src.plugins.repeat import plugin_config
from src.plugins.repeat.recorder import get_recorder


async def need_repeat(event: Event, user: UserSession) -> bool:
    """是否复读这个消息"""
    # 不复读配置中排除的用户
    if user.user_name in plugin_config.repeat_excluded_users or user.user_id in plugin_config.repeat_excluded_users:
        return False

    # 不复读对机器人说的，因为这个应该由闲聊插件处理
    if event.is_tome():
        return False

    # 只复读指定群内消息
    recorder = get_recorder(user.session_id)
    if not await recorder.is_enabled():
        return False

    # 不要复读指令
    if event.get_plaintext().startswith("/"):
        return False

    # 记录群内发送消息数量和时间
    now = datetime.now()
    recorder.add_msg_send_time(now)

    # 不要复读应用消息
    if user.platform == "QQClient" and user.platform_user.id == "1000000":
        return False

    # 不要复读签到，分享，小程序，转发，红包
    if event.get_message()[0].type in ["sign", "share", "json", "forward", "redbag"]:
        return False

    # 不要复读带网址的消息
    if "http://" in event.get_plaintext().lower() or "https://" in event.get_plaintext().lower():
        return False

    # 复读之后一定时间内不再复读
    time = recorder.last_message_on()
    if time is not None and now < time + timedelta(minutes=plugin_config.repeat_interval):
        return False

    # 按照设定概率复读
    random = secrets.SystemRandom()
    rand = random.randint(1, 100)
    logger.info(f"repeat: {rand}")
    if rand > plugin_config.repeat_rate:
        # 未复读时，仅记录消息数量
        await recorder.add_msg_number_list(user.user_id)
        return False

    await recorder.add_repeat_list(user.user_id)
    # 记录复读时间
    recorder.reset_last_message_on()

    return True
