'''复读插件'''
import re
from datetime import datetime, timedelta
from random import randint

from coolqbot.bot import bot
from coolqbot.logger import logger


class Recorder(object):
    def __init__(self):
        self.last_message_on = datetime.utcnow()


recorder = Recorder()


def is_repeat(recorder, msg):
    if msg['group_id'] != 438789224:
        return False

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

    rand = randint(1, 100)
    logger.info(rand)
    if rand > 15:
        return False

    time = recorder.last_message_on
    if datetime.utcnow() < time + timedelta(minutes=1):
        return False
    recorder.last_message_on = datetime.utcnow()

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
