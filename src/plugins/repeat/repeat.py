""" 复读
"""
import re
import secrets
from datetime import datetime, timedelta

from nonebot import CommandSession, logger

from . import DATA
from .recorder import recorder

# 复读概率
REPEAT_RATE = int(DATA.get_config('repeat', 'repeat_rate', fallback='10'))
# 复读间隔
REPEAT_INTERVAL = int(DATA.get_config('repeat', 'repeat_interval', fallback='1'))


def is_repeat(session: CommandSession, message: str):
    """ 是否复读这个消息 """
    group_id = session.ctx['group_id']
    user_id = session.ctx['sender']['user_id']
    # 只复读指定群内消息
    if group_id not in session.bot.config.GROUP_ID:
        return False

    # 不要复读指令
    match = re.match(r'^\/', message)
    if match:
        return False

    # 记录群内发送消息数量和时间
    now = datetime.now()
    recorder.add_msg_send_time(now, group_id)

    # 如果不是PRO版本则不复读纯图片
    match = re.search(r'\[CQ:image[^\]]+\]$', message)
    if match and not session.bot.config.IS_COOLQ_PRO:
        return False

    # 不要复读应用消息
    if user_id == 1000000:
        return False

    # 不要复读签到，分享
    match = re.match(r'^\[CQ:(sign|share).+\]', message)
    if match:
        return False

    # 复读之后1分钟之内不再复读
    time = recorder.last_message_on(group_id)
    if now < time + timedelta(minutes=REPEAT_INTERVAL):
        return False

    repeat_rate = REPEAT_RATE
    # 当10分钟内发送消息数量大于30条时，降低复读概率
    # 因为排行榜需要固定概率来展示欧非，暂时取消
    # if recorder.message_number(10) > 30:
    #     logger.info('Repeat rate changed!')
    #     repeat_rate = 5

    # 记录每个人发送消息数量
    recorder.add_msg_number_list(user_id, group_id)

    # 按照设定概率复读
    random = secrets.SystemRandom()
    rand = random.randint(1, 100)
    logger.info(f'repeat: {rand}')
    if rand > repeat_rate:
        return False

    # 记录复读时间
    recorder.reset_last_message_on(group_id)

    # 记录复读次数
    recorder.add_repeat_list(user_id, group_id)

    return True
