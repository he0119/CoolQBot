""" FF14

一些最终幻想XIV相关的指令
"""
import json

import aiohttp
from nonebot import CommandSession, on_command

from coolqbot import PluginData, bot

DATA = PluginData('ff14', config=True)
MONITOR_SERVER_STATUS = bool(
    int(DATA.config_get('ff14', 'monitor_server_status', '0'))
)
MONITOR_SERVER_STATUS_JOB = None
MONITOR_SERVER_STATUS_DATA = None


@on_command(
    'ff14', aliases=['最终幻想14', '最终幻想XIV'], only_to_me=False, shell_like=True
)
async def ff14(session: CommandSession):
    """ 最终幻想XIV
    """
    global MONITOR_SERVER_STATUS, MONITOR_SERVER_STATUS_JOB
    if session.argv[0] == 'server' and len(session.argv) == 1:
        if MONITOR_SERVER_STATUS:
            session.finish('正在监控服务器状态，我会在服务器状态发生变化时提醒你')
        else:
            session.finish('当前没有检测服务器状态')
    if session.argv[0] == 'server' and len(session.argv) == 2:
        if session.argv[1].lower() in ['0', 'off', 'false']:
            if MONITOR_SERVER_STATUS_JOB:
                MONITOR_SERVER_STATUS_JOB.remove()
                MONITOR_SERVER_STATUS = False
                DATA.config_set('ff14', 'monitor_server_status', '0')
            session.finish('已停止监测服务器状态')
        else:
            if not MONITOR_SERVER_STATUS_JOB:
                MONITOR_SERVER_STATUS_JOB = bot.scheduler.add_job(
                    monitor_server_status, 'interval', seconds=1
                )
                MONITOR_SERVER_STATUS = True
                DATA.config_set('ff14', 'monitor_server_status', '1')
            session.finish('已开始监测服务器状态')

    session.finish('抱歉，并没有这个功能。')


async def monitor_server_status():
    """ 监控服务器状态 """
    global MONITOR_SERVER_STATUS_DATA
    group_id = bot.get_bot().config.GROUP_ID[0]
    if not MONITOR_SERVER_STATUS_DATA:
        MONITOR_SERVER_STATUS_DATA = await get_server_status()
        await bot.get_bot().send_msg(
            message_type='group',
            group_id=group_id,
            message=str(MONITOR_SERVER_STATUS_DATA)
        )
    else:
        now = await get_server_status()
        if MONITOR_SERVER_STATUS_DATA == now:
            pass
        else:
            MONITOR_SERVER_STATUS_DATA = await get_server_status()
            await bot.get_bot().send_msg(
                message_type='group',
                group_id=group_id,
                message=str(MONITOR_SERVER_STATUS_DATA)
            )


async def get_server_status():
    """ 获取服务器状态 """
    url = 'http://39.100.233.51/status'
    try:
        # 使用 aiohttp 库发送最终的请求
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url) as response:
                if response.status != 200:
                    # 如果 HTTP 响应状态码不是 200，说明调用失败
                    return None

                resp_payload = json.loads(await response.text())

                return {
                    '陆行鸟': resp_payload['luxingniao'],
                    '莫古力': resp_payload['moguli'],
                    '猫小胖': resp_payload['maoxiaopang']
                }
    except (aiohttp.ClientError, json.JSONDecodeError, KeyError):
        # 抛出上面任何异常，说明调用失败
        return None
