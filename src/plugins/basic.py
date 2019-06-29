""" 基础插件
"""
from nonebot import (CommandSession, IntentCommand, NLPSession, on_command,
                     on_natural_language, permission)

from coolqbot import bot


@on_command('whoami',
            aliases={'我是谁'},
            permission=permission.GROUP,
            only_to_me=False)
async def whoami(session: CommandSession):
    msg = await session.bot.get_group_member_info(
        user_id=session.ctx['sender']['user_id'],
        group_id=session.ctx['group_id'],
        no_cache=True)
    if msg['card']:
        outName = msg['card']
    else:
        outName = msg['nickname']
    await session.send(f'你是{outName}!')


@on_command('whereami',
            aliases={'我在哪'},
            permission=permission.GROUP,
            only_to_me=False)
async def whereami(session: CommandSession):
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


@on_natural_language(keywords={'我是谁'}, permission=permission.GROUP)
async def _(session: NLPSession):
    return IntentCommand(90.0, 'whoami')


@on_natural_language(keywords={'我在哪'}, permission=permission.GROUP)
async def _(session: NLPSession):
    return IntentCommand(90.0, 'whereami')


@on_natural_language(keywords={'你是谁'})
async def _(session: NLPSession):
    return IntentCommand(90.0, 'whoareyou')


@on_natural_language(keywords={'我在干什么', '我在做什么'})
async def _(session: NLPSession):
    return IntentCommand(90.0, 'whatiamdoing')
