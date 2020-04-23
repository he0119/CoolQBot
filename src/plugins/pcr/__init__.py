""" 公主连结Re:Dive

https://github.com/yuudi/yobot
"""
import asyncio
import subprocess
from pathlib import Path
import requests
import json

from nonebot import CommandSession, get_bot, on_command, scheduler

from coolqbot import PluginData

# 下载 Yobot
YOBOT_DIR = Path(__file__).resolve().parent / 'yobot'


def download_yobot(force=False):
    """ 下载 Yobot

    force: 是否强制下载，如是则先删除文件夹内文件之后再下载
    """
    if force:
        pass
    else:
        subprocess.run(
            f'cd "{YOBOT_DIR.parent}" && git clone https://gitee.com/yobot/yobot.git',
            shell=True,
            check=True
        )


def configure_yobot():
    """ 运行前配置 """
    yobot_init_file: Path = YOBOT_DIR / '__init__.py'
    # 如果有 init 文件，则删除
    if yobot_init_file.exists():
        yobot_init_file.unlink()


def update_yobot(ver_id: int):
    check_url = [
        'https://gitee.com/yobot/yobot/raw/master/docs/v3/ver.json',
        'https://yuudi.github.io/yobot/v3/ver.json',
        'http://api.yobot.xyz/v3/version/'
    ]
    for url in check_url:
        try:
            response = requests.get(url)
        except requests.ConnectionError:
            continue
        if response.status_code == 200:
            server_available = True
            break
    if not server_available:
        return '无法连接服务器'
    verinfo = json.loads(response.text)
    verinfo = verinfo['stable']
    if not (verinfo['version'] > ver_id):
        return '已经是最新版本'

    subprocess.run(
        f'cd "{YOBOT_DIR}" && git checkout . && git pull',
        shell=True,
        check=True
    )
    return '升级成功，请重新启动'


if not YOBOT_DIR.exists():
    download_yobot()

# 配置 Yobot
configure_yobot()

from .yobot.src.client.yobot import Yobot

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
    if session.argv[0] in ['更新', '强制更新'] and len(session.argv) == 1:
        ver_id = 3300 + sum(Yobot.Commit.values())
        reply = update_yobot(ver_id)
        session.finish(reply)

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
