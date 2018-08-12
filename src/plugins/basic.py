# -*- coding: utf-8 -*-
import re
from datetime import datetime, timedelta
from random import randint

from coolqbot.bot import bot
from coolqbot.logger import logger


# =====复读插件=====
class Recorder(object):
    def __init__(self):
        self.last_message_on = datetime.utcnow()


recorder = Recorder()


def is_repeat(recorder, msg):
    if msg['group_id'] != 438789224:
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
    print(rand)
    if rand > 15:
        return False

    time = recorder.last_message_on
    if datetime.utcnow() < time + timedelta(minutes=1):
        return False
    recorder.last_message_on = datetime.utcnow()

    return True


@bot.on_message('group')
async def repeat(context):
    global recorder
    logger.debug(context)
    if is_repeat(recorder, context):
        return {'reply': context['message'], 'at_sender': False}


@bot.on_message('group')
async def nick_call(context):
    if '/我是谁' == context['message']:
        msg = await bot.get_stranger_info(user_id=context['user_id'])
        return {'reply': f'你是{msg["nickname"]}!'}

    elif '/我在哪' == context['message']:
        group_list = await bot.get_group_list()
        for group in group_list:
            if group['group_id'] == context['group_id']:
                return {'reply': f'你在{group["group_name"]}!'}

    elif context['message'] in ('/我在干什么', '/我在做什么'):
        return {'reply': '你在调戏我!!'}


@bot.on_message()
async def on_message(context):
    logger.debug(context)
