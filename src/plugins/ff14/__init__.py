""" FF14

一些最终幻想XIV相关的指令
"""
from nonebot import CommandSession, on_command

from coolqbot import bot

from .monitor_server import server_monitor


@on_command(
    'ff14', aliases=['最终幻想14', '最终幻想XIV'], only_to_me=False, shell_like=True
)
async def ff14(session: CommandSession):
    """ 最终幻想XIV
    """
    user_id = session.ctx['user_id']
    if len(session.argv) == 0:
        session.finish('当前支持的功能有\nserver：查询服务器在线状态')
    if session.argv[0] == 'server' and len(session.argv) == 1:
        session.finish(server_monitor.status)
    if session.argv[0] == 'server' and len(session.argv) == 2:
        if session.argv[1].lower() in ['0', 'off', 'false']:
            if server_monitor.is_enabled:
                server_monitor.disable()
            session.finish('已停止监控服务器状态')
        else:
            if not server_monitor.is_enabled:
                server_monitor.enable()
            session.finish('已开始监控服务器状态')

    session.finish('抱歉，并没有这个功能。')
