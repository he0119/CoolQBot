'''复读插件'''
import re
from datetime import datetime, timedelta
from random import randint

from coolqbot.bot import bot
from coolqbot.logger import logger


class Recorder(object):
    def __init__(self):
        self.last_message_on = datetime.utcnow()
        self.msg_send_time = []


recorder = Recorder()


def message_number(recorder):
    '''返回5分钟内的消息条数'''
    times = recorder.msg_send_time
    now = datetime.utcnow()
    for i in range(len(times)):
        if times[i] > now - timedelta(minutes=5):
            recorder.msg_send_time = recorder.msg_send_time[i:]
            logger.debug(len(recorder.msg_send_time))
            return len(recorder.msg_send_time)
    logger.debug(len(recorder.msg_send_time))
    return len(recorder.msg_send_time)


def is_repeat(recorder, msg):
    if msg['group_id'] != 438789224:
        return False

    now = datetime.utcnow()
    # 记录群内发送消息数量和时间
    recorder.msg_send_time.append(now)

    # 不要复读过长的文字
    if len(msg['message']) > 28:
        return False

    # 不要复读图片，签到，分享
    match = re.match(r'^\[CQ:(image|sign|share).+\]', msg['message'])
    if match:
        return False

    # 不要复读指令
    match = re.match(r'^\/|!', msg['message'])
    if match:
        return False

    repeat_rate = 15
    # 当5分钟内发送消息数量大于25条时，降低概率
    if message_number(recorder) > 25:
        logger.debug('Repeat rate changed!')
        repeat_rate = 5

    rand = randint(1, 100)
    logger.info(rand)
    if rand > repeat_rate:
        return False

    # 复读之后1分钟之内不再复读
    time = recorder.last_message_on
    if datetime.utcnow() < time + timedelta(minutes=1):
        return False

    recorder.last_message_on = now

    return True


@bot.on_message('group')
async def repeat(context):
    '''人类本质'''
    global recorder
    if is_repeat(recorder, context):
        return {'reply': context['message'], 'at_sender': False}


@bot.on_message('group')
async def repeat_sign(context):
    '''复读签到(电脑上没法看手机签到内容)'''
    if context['group_id'] == 438789224:
        match = re.match(r'^\[CQ:sign(.+)\]$', context['message'])
        if match:
            title = re.findall(r'title=(\w+\s?\w+)', context['message'])
            return {'reply': f'今天的运势是{title[0]}'}
