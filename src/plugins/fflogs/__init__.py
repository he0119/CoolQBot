""" FFLogs

从网站 https://cn.fflogs.com/ 获取输出数据
"""
import asyncio

from nonebot import CommandSession, on_command

from coolqbot import bot

from .api import API
from .data import DATA, get_bosses_info, get_jobs_info

HOUR = int(DATA.config_get('cache', 'hour', fallback='4'))
MINUTE = int(DATA.config_get('cache', 'minute', fallback='30'))
SECOND = int(DATA.config_get('cache', 'second', fallback='0'))


@bot.scheduler.scheduled_job(
    'cron', hour=HOUR, minute=MINUTE, second=SECOND, id='fflogs_cache'
)
async def fflogs_cache():
    """ 定时缓存数据
    """
    bosses = get_bosses_info()
    jobs = get_jobs_info()
    for boss in bosses:
        for job in jobs:
            await API.dps(boss.name, job.name)
            bot.logger.debug(f'{boss.name} {job.name}的数据缓存完成。')
            await asyncio.sleep(30)


@on_command('dps', aliases=['输出'], only_to_me=False, shell_like=True)
async def dps(session: CommandSession):
    """ 查询 DPS
    """
    user_id = session.ctx['user_id']
    # 设置 Token
    if session.argv[0] == 'token' and len(session.argv) == 2:
        # 检查是否是超级用户
        if user_id not in session.bot.config.SUPERUSERS:
            session.finish('抱歉，你没有权限修改 Token。')

        API.token = session.argv[1]
        session.finish('Token 设置完成。')

    # 检查 Token 是否设置
    if not API.token:
        session.finish(
            '对不起，Token 未设置，无法查询数据。\n请先使用命令\n/dps token <token>\n配置好 Token 后再尝试查询数据。'
        )

    if session.argv[0] == 'token' and len(session.argv) == 1:
        # 检查是否是超级用户
        if user_id not in session.bot.config.SUPERUSERS:
            session.finish('抱歉，你没有权限查看 Token。')
        session.finish(f'当前的 Token 为 {API.token}')

    if session.argv[0] == 'me' and len(session.argv) == 1:
        if user_id not in API.characters:
            session.finish(
                '抱歉，你没有绑定最终幻想14的角色。\n请使用\n/dps me <角色名> <服务器名>\n绑定自己的角色。'
            )
        session.finish(
            f'你当前绑定的角色：\n角色：{API.characters[user_id][0]}\n服务器：{API.characters[user_id][1]}'
        )

    if session.argv[0] == 'me' and len(session.argv) == 3:
        API.set_character(user_id, session.argv[1], session.argv[2])
        session.finish('角色绑定成功！')

    if session.argv[0] == 'classes' and len(session.argv) == 1:
        reply = await API.classes()
        session.finish(str(reply))

    if session.argv[0] == 'zones' and len(session.argv) == 2:
        reply = await API.zones()
        session.finish(str(reply[int(session.argv[1])]))

    # 判断查询排行是指个人还是特定职业
    if len(session.argv) == 2:
        # <BOSS名> me
        # <BOSS名> <职业名>
        if session.argv[1].lower() in ['me', 'i', '我']:
            if user_id not in API.characters:
                session.finish(
                    '抱歉，你没有绑定最终幻想14的角色。\n请使用\n/dps me <角色名> <服务器名>\n绑定自己的角色。'
                )
            reply = await API.character_dps(
                session.argv[0], *API.characters[user_id]
            )
        else:
            reply = await API.dps(*session.argv)
        session.finish(reply)

    if len(session.argv) == 3:
        # <BOSS名> <职业名> <DPS种类>
        # <BOSS名> <角色名> <服务器名>
        if session.argv[2] in ['adps', 'rdps', 'pdps']:
            reply = await API.dps(*session.argv)
        else:
            reply = await API.character_dps(*session.argv)
        session.finish(reply)

    session.finish('抱歉，并没有这个功能。')
