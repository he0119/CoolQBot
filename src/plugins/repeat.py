'''复读插件'''
import re
from datetime import datetime, timedelta
from random import randint

from coolqbot.bot import bot
from coolqbot.recorder import recorder


def is_repeat(recorder, msg):
    # 只复读特定群内消息
    if msg['group_id'] != 438789224:
        return False

    # 不要复读指令
    match = re.match(r'^\/|!', msg['message'])
    if match:
        return False

    # 记录群内发送消息数量和时间
    now = datetime.utcnow()
    recorder.msg_send_time.append(now)

    # 不要复读过长的文字
    if len(msg['message']) > 28:
        return False

    # 不要复读图片，签到，分享
    match = re.match(r'^\[CQ:(image|sign|share).+\]', msg['message'])
    if match:
        return False

    # 复读之后1分钟之内不再复读
    time = recorder.last_message_on
    if datetime.utcnow() < time + timedelta(minutes=1):
        return False

    repeat_rate = 15
    # 当10分钟内发送消息数量大于30条时，降低复读概率
    if recorder.message_number(10) > 30:
        bot.logger.debug('Repeat rate changed!')
        repeat_rate = 5

    # 按照设定概率复读
    rand = randint(1, 100)
    bot.logger.info(rand)
    if rand > repeat_rate:
        return False

    # 记录复读时间
    recorder.last_message_on = now

    #记录复读次数
    recorder.add_to_repeat_list(msg['user_id'])

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
