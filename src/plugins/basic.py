'''基础插件'''
import re

from coolqbot.bot import bot
from coolqbot.recorder import recorder
from coolqbot.utils import scheduler


# @scheduler.scheduled_job('interval', minutes=1)
# async def coolq_status():
#     '''检查酷Q状态'''
#     #FIXME:检查状态的时候会出错(似乎是插件的问题，只能暂时等一等，先用着以前的docker image吧)
#     try:
#         msg = await bot.get_status()
#         if not msg['good']:
#             await bot.set_restart()
#             bot.logger.info('重启酷Q')
#     except:
#         bot.logger.error('无法获取酷Q状态')


@bot.on_message('group')
async def nick_call(context):
    if '/我是谁' == context['message']:
        # msg = await bot.get_stranger_info(user_id=context['user_id'])
        cardName = context['sender']['card']
        return {'reply': f'你是{cardName}!'}

    elif '/我在哪' == context['message']:
        group_list = await bot.get_group_list()
        msg = await bot.get_group_member_info(user_id = context['user_id'],group_id = context['group_id'])
        for group in group_list:
            if group['group_id'] == context['group_id']:
                return {'reply': f'\n你所在群：{group["group_name"]}\n你所在地区：{msg["area"]}'}

    elif '/你是谁' == context['message']:
        msg = await bot.get_group_member_info(user_id = context['self_id'],group_id = context['group_id'])
        return {'reply': f'我是{msg["card"]}!'}
        # return {'reply': '我是可爱的小誓约!'}

    elif context['message'] in ('/我在干什么', '/我在做什么'):
        return {'reply': '你在调戏我!!'}


@bot.on_message()
async def on_message(context):
    bot.logger.info(context)
