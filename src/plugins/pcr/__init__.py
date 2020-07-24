""" 公主连结Re:Dive

https://github.com/yuudi/yobot
"""
import asyncio

from nonebot import CommandSession, get_bot, on_command, scheduler

from coolqbot import PluginData
from yobot.yobot import Yobot

DATA = PluginData('pcr')

verinfo = {
    "run-as": "nonebot-plugin",
    "ver_name": "yobot{}".format(Yobot.Version),
}

cqbot = get_bot()
bot = Yobot(
    data_path=str(DATA._base_path),
    verinfo=verinfo,
    scheduler=scheduler,
    quart_app=cqbot.server_app,
    bot_api=cqbot._api,
)


@on_command('pcr', aliases=['公主连结'], shell_like=True, only_to_me=False)
async def handle_msg(session: CommandSession):
    if len(session.argv) == 0:
        session.finish('欢迎使用 公主连结Re:Dive 小助手~\n请输入 /pcr help 来获取帮助')

    ctx = session.event.copy()
    # 去除命令，因为 yobot 不需要
    ctx['raw_message'] = ctx['raw_message'].split(maxsplit=1)[1]

    reply = await bot.proc_async(ctx)
    if reply != "" and reply is not None:
        session.finish(reply)


async def send_it(func):
    if asyncio.iscoroutinefunction(func):
        to_sends = await func()
    else:
        to_sends = func()
    if to_sends is None:
        return
    tasks = [cqbot.send_msg(**kwargs) for kwargs in to_sends]
    await asyncio.gather(*tasks)


jobs = bot.active_jobs()
if jobs:
    for trigger, job in jobs:
        scheduler.add_job(
            func=send_it,
            args=(job, ),
            trigger=trigger,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=60,
        )

__plugin_name__ = 'pcr'
__plugin_usage__ = 'pcr assistant'
