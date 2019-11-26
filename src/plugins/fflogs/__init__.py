""" fflogs

从网站 https://cn.fflogs.com/ 获取输出数据
文档网址 https://cn.fflogs.com/v1/docs
"""
from nonebot import CommandSession, on_command

from coolqbot import bot

from .api import API


@on_command('dps', aliases=['输出'], only_to_me=False, shell_like=True)
async def dps(session: CommandSession):
    """ 查询 DPS
    """
    # 设置 Token
    if len(session.argv) == 2 and session.argv[0] == 'token':
        API.token = session.argv[1]
        session.finish('Token 设置完成。')

    # 检查 Token 是否设置
    if not API.token:
        session.finish(
            '对不起，Token 未设置，无法查询数据。\n请先使用命令\n/dps token <token>\n配置好 Token 后再尝试查询数据。'
        )

    if session.argv[0] == 'token' and len(session.argv) == 1:
        session.finish(f'当前的 Token 为 {API.token}')

    if session.argv[0] == 'classes' and len(session.argv) == 1:
        reply = await API.classes()
        session.finish(str(reply))

    if session.argv[0] == 'zones' and len(session.argv) == 2:
        reply = await API.zones()
        session.finish(str(reply[int(session.argv[1])]))

    if len(session.argv) > 1 and len(session.argv) < 4:
        reply = await API.dps(*session.argv)
        session.finish(reply)

    session.finish('抱歉，并没有这个功能。')
