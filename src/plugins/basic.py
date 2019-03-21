""" 基础插件
"""
import re

from coolqbot.bot import bot
from coolqbot.utils import scheduler
from plugins.recorder import recorder


@scheduler.scheduled_job('interval', seconds=5)
async def coolq_status():
    """ 检查酷Q状态

    每5秒检查一次状态，并记录
    """
    try:
        msg = await bot.get_status()
        bot.logger.debug(msg)
        recorder.coolq_status = msg['good']
    except:
        bot.logger.error('无法获取酷Q状态')


@scheduler.scheduled_job('interval', minutes=1)
async def reboot():
    """ 查看是否需要重启

    每分钟检查一次酷Q状态
    如果状态不好自动重启
    """
    if not recorder.coolq_status:
        await bot.set_restart()
        recorder.coolq_status = False
        recorder.is_restart = True
        recorder.send_hello = False
        bot.logger.info('重启酷Q')


@bot.on_message('group')
async def nick_call(context):
    if '/我是谁' == context['message']:
        # msg = await bot.get_stranger_info(user_id=context['user_id'])
        msg = await bot.get_group_member_info(user_id=context['user_id'], group_id=context['group_id'], no_cache=True)
        if msg['card']:
            outName = msg['card']
        else:
            outName = msg['nickname']
        return {'reply': f'你是{outName}!'}

    elif '/我在哪' == context['message']:
        group_list = await bot.get_group_list()
        msg = await bot.get_group_member_info(user_id=context['user_id'], group_id=context['group_id'], no_cache=True)
        if msg['area']:
            country = msg['area']
        else:
            country = '不知道不关心'
        for group in group_list:
            if group['group_id'] == context['group_id']:
                return {'reply': f'\n你所在群：{group["group_name"]}\n你所在地区：{country}'}

    elif '/你是谁' == context['message']:
        return {'reply': '我是可爱的小誓约!'}

    elif context['message'] in ('/我在干什么', '/我在做什么'):
        return {'reply': '你在调戏我!!'}


@bot.on_message()
async def on_message(context):
    bot.logger.info(context)
