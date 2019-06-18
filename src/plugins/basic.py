""" 基础插件
"""
from nonebot import CommandSession, on_command

from coolqbot import bot

from .recorder import recorder


@bot.scheduler.scheduled_job('interval', seconds=5, id='coolq_status')
async def coolq_status():
    """ 检查酷Q状态

    每5秒检查一次状态，并记录
    """
    try:
        msg = await bot.get_bot().get_status()
        recorder.coolq_status = msg['good']
    except:
        bot.logger.error('无法获取酷Q状态')


@on_command('whoami', aliases={'我是谁'}, only_to_me=False)
async def whoami(session: CommandSession):
    if session.ctx['message_type'] == 'group':
        msg = await session.bot.get_group_member_info(
            user_id=session.ctx['sender']['user_id'],
            group_id=session.ctx['group_id'],
            no_cache=True)
        if msg['card']:
            outName = msg['card']
        else:
            outName = msg['nickname']
        await session.send(f'你是{outName}!')


@on_command('whereami', aliases={'我在哪'}, only_to_me=False)
async def whereami(session: CommandSession):
    if session.ctx['message_type'] == 'group':
        group_list = await session.bot.get_group_list()
        msg = await session.bot.get_group_member_info(
            user_id=session.ctx['sender']['user_id'],
            group_id=session.ctx['group_id'],
            no_cache=True)
        if msg['area']:
            country = msg['area']
        else:
            country = '不知道不关心'
        for group in group_list:
            if group['group_id'] == session.ctx['group_id']:
                await session.send(
                    f'\n你所在群：{group["group_name"]}\n你所在地区：{country}',
                    at_sender=True)


@on_command('whoareyou', aliases={'你是谁'}, only_to_me=False)
async def whoareyou(session: CommandSession):
    await session.send('我是可爱的小誓约！')


@on_command('whatiamdoing', aliases={'我在干什么', '我在做什么'}, only_to_me=False)
async def whatiamdoing(session: CommandSession):
    await session.send('你在调戏我！！')
