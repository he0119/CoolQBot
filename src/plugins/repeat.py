""" 复读插件
"""
import re
import secrets
from datetime import datetime, timedelta

from nonebot import (CommandSession, IntentCommand, NLPSession, on_command,
                     on_natural_language, on_notice)

from coolqbot import PluginData, bot

from .recorder import recorder

DATA = PluginData('repeat', config=True)
# 复读概率
REPEAT_RATE = int(DATA.config_get('bot', 'repeat_rate', fallback='10'))
# 复读间隔
REPEAT_INTERVAL = int(DATA.config_get('bot', 'repeat_interval', fallback='1'))


def is_repeat(session: CommandSession, message):
    # 只复读指定群内消息
    if session.ctx['group_id'] != session.bot.config.GROUP_ID:
        return False

    # 不要复读指令
    match = re.match(r'^\/', message)
    if match:
        return False

    # 记录群内发送消息数量和时间
    now = datetime.now()
    recorder.add_msg_send_time(now)

    # 如果不是PRO版本则不复读纯图片
    match = re.search(r'\[CQ:image[^\]]+\]$', message)
    if match and not session.bot.config.IS_COOLQ_PRO:
        return False

    # 不要复读应用消息
    if session.ctx['sender']['user_id'] == 1000000:
        return False

    # 不要复读签到，分享
    match = re.match(r'^\[CQ:(sign|share).+\]', message)
    if match:
        return False

    # 复读之后1分钟之内不再复读
    time = recorder.last_message_on
    if datetime.now() < time + timedelta(minutes=REPEAT_INTERVAL):
        return False

    repeat_rate = REPEAT_RATE
    # 当10分钟内发送消息数量大于30条时，降低复读概率
    # 因为排行榜需要固定概率来展示欧非，暂时取消
    # if recorder.message_number(10) > 30:
    #     bot.logger.info('Repeat rate changed!')
    #     repeat_rate = 5

    # 记录每个人发送消息数量
    recorder.add_msg_number_list(session.ctx['sender']['user_id'])

    # 按照设定概率复读
    random = secrets.SystemRandom()
    rand = random.randint(1, 100)
    bot.logger.info(f'repeat: {rand}')
    if rand > repeat_rate:
        return False

    # 记录复读时间
    recorder.last_message_on = now

    # 记录复读次数
    recorder.add_repeat_list(session.ctx['sender']['user_id'])

    return True


@on_command('repeat')
async def repeat(session: CommandSession):
    """ 人类本质
    """
    message = session.state.get('message')
    if is_repeat(session, message):
        await session.send(message)


@on_command('repeat_sign')
async def repeat_sign(session: CommandSession):
    """ 复读签到（电脑上没法看手机签到内容）
    """
    if session.ctx['group_id'] == session.bot.config.GROUP_ID:
        title = re.findall(r'title=(\w+\s?\w+)', session.state.get('message'))
        await session.send(f'今天的运势是{title[0]}', at_sender=True)


@on_natural_language(only_to_me=False)
async def _(session: NLPSession):
    # 只复读群消息，与没有对机器人说的话
    if session.ctx['message_type'] == 'group' and not session.ctx['to_me']:
        # 以置信度 60.0 返回 repeat 命令
        # 确保任何消息都在且仅在其它自然语言处理器无法理解的时候使用 repeat 命令
        return IntentCommand(60.0, 'repeat', args={'message': session.msg})


@on_natural_language(only_to_me=False)
async def _(session: NLPSession):
    match = re.match(r'^\[CQ:sign(.+)\]$', session.msg)
    if match:
        return IntentCommand(90.0,
                             'repeat_sign',
                             args={'message': session.msg})
