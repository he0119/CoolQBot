""" fflogs

从网站 https://cn.fflogs.com/ 获取输出数据
"""
from nonebot import CommandSession, on_command

from coolqbot import PluginData, bot

DATA = PluginData('fflogs', config=True)


@on_command('dps', aliases=['输出'], only_to_me=False, shell_like=True)
async def dps(session: CommandSession):
    """ 查询 DPS
    """
    # 设置 Token
    if len(session.argv) == 2 and session.argv[0] == 'token':
        DATA.config_set('fflogs', 'token', session.argv[1])
        session.finish('Token 设置完成。')

    # 读取 Token
    try:
        token = DATA.config_get('fflogs', 'token')
    except:
        session.finish(
            '对不起，Token 未设置，无法查询数据。\n请先使用命令\n/dps token <token>\n配置好 Token 后再尝试查询数据。'
        )

    if len(session.argv) == 0:
        session.finish('这个功能还没有实现。')
    elif len(session.argv) == 1:
        if session.argv[0] == 'token':
            session.finish(f'当前的 Token 为 {token}')
        session.finish('这个功能还没有实现。')
    elif len(session.argv) == 2:
        session.finish('这个功能还没有实现。')
    elif len(session.argv) > 2:
        session.finish('这个功能还没有实现。')
