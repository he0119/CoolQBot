""" 复读插件
"""
import re
import secrets
from datetime import datetime, timedelta

from coolqbot.bot import bot
from coolqbot.config import GROUP_ID, IS_COOLQ_PRO
from plugins.recorder import recorder


def is_repeat(msg):
    # 只复读指定群内消息
    if msg['group_id'] != GROUP_ID:
        return False

    # 不要复读指令
    match = re.match(r'\/', msg['message'])
    if match:
        return False

    # 不要复读@机器人的消息
    match = re.search(r'\[CQ:at,qq=2062765419\]', msg['message'])
    if match:
        return False

    # 记录群内发送消息数量和时间
    now = datetime.utcnow()
    recorder.msg_send_time.append(now)

    # 如果不是PRO版本则不复读纯图片
    match = re.search(r'^\[CQ:image[^\]]+\]$', msg['message'])
    if match and not IS_COOLQ_PRO:
        return False

    # 不要复读应用消息
    if msg['sender']['user_id'] == 1000000:
        return False

    # 不要复读签到，分享
    match = re.match(r'\[CQ:(sign|share).+\]', msg['message'])
    if match:
        return False

    # 不要复读过长的文字
    new_msg = re.sub(r'\[CQ:[^\]]+\]', '', msg['raw_message'])
    if len(new_msg) > 28:
        return False

    # 复读之后1分钟之内不再复读
    time = recorder.last_message_on
    if datetime.utcnow() < time + timedelta(minutes=1):
        return False

    repeat_rate = 10
    # 当10分钟内发送消息数量大于30条时，降低复读概率
    # 因为排行榜需要固定概率来展示欧非，暂时取消
    # if recorder.message_number(10) > 30:
    #     bot.logger.info('Repeat rate changed!')
    #     repeat_rate = 5

    # 记录每个人发送消息数量
    recorder.add_to_list(recorder.msg_number_list, msg['user_id'])

    # 按照设定概率复读
    random = secrets.SystemRandom()
    rand = random.randint(1, 100)
    bot.logger.info(rand)
    if rand > repeat_rate:
        return False

    # 记录复读时间
    recorder.last_message_on = now

    # 记录复读次数
    recorder.add_to_list(recorder.repeat_list, msg['user_id'])

    return True


@bot.on_message('group')
async def repeat(context):
    """ 人类本质
    """
    if is_repeat(context):
        return {'reply': context['message'], 'at_sender': False}


@bot.on_message('group')
async def repeat_sign(context):
    """ 复读签到(电脑上没法看手机签到内容)
    """
    if context['group_id'] == GROUP_ID:
        match = re.match(r'^\[CQ:sign(.+)\]$', context['message'])
        if match:
            title = re.findall(r'title=(\w+\s?\w+)', context['message'])
            return {'reply': f'今天的运势是{title[0]}'}
