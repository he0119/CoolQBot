""" 公主连结Re:Dive

版本 3378
https://github.com/yuudi/yobot
"""
import asyncio

from nonebot import CommandSession, get_bot, on_command, scheduler

from .src.client.yobot import Yobot

verinfo = {
    "run-as": "nonebot-plugin",
    "ver_name": "yobot{}插件版".format(Yobot.Version),
}

cqbot = get_bot()
bot = Yobot(
    data_path="./yobot_data",
    verinfo=verinfo,
    scheduler=scheduler,
    quart_app=cqbot.server_app,
    bot_api=cqbot._api,
)


@on_command('pcr', only_to_me=False)
async def handle_msg(session: CommandSession):
    ctx = session.ctx.copy()
    ctx['raw_message'] = ctx['raw_message'][5:]

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
