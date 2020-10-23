""" 最终幻想XIV

各种小工具
"""
from nonebot import CommandGroup
from nonebot.typing import Bot, Event

from src.utils.helpers import strtobool

from .config import config
from .fflogs_api import fflogs
from .gate import get_direction
from .news import news

ff14 = CommandGroup('ff14', priority=1, block=True)

#region 藏宝选门
gate_cmd = ff14.command('gate', aliases={'gate'})
gate_cmd.__doc__ = """
gate

最终幻想XIV藏宝选门

选择门的数量
/gate 2
/gate 3
"""


@gate_cmd.args_parser
async def gate_args_parser(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()

    if not stripped_arg:
        await gate_cmd.reject('你什么都不输入我怎么知道呢，请告诉我有几个门！')

    if stripped_arg not in ['2', '3']:
        await gate_cmd.reject('暂时只支持两个门或者三个门的情况，请重新输入吧。')

    state['door_number'] = int(stripped_arg)


@gate_cmd.handle()
async def handle_first_gate(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()
    if stripped_arg in ['2', '3']:
        state['door_number'] = int(stripped_arg)


@gate_cmd.got('door_number', prompt='总共有多少个门呢？')
async def handle_gate(bot: Bot, event: Event, state: dict):
    direction = get_direction(state['door_number'])
    await gate_cmd.finish(direction)


#endregion
#region 新闻推送
news_cmd = ff14.command('news')
news_cmd.__doc__ = """
ff14.news

最终幻想XIV新闻推送

开启推送
/ff14.news on
关闭推送
/ff14.news off
在本群启用
/ff14.news enable
在本群禁用
/ff14.news disable
"""


@news_cmd.handle()
async def handle_first_news(bot: Bot, event: Event, state: dict):
    stripped_arg = str(event.message).strip()
    if stripped_arg:
        if strtobool(stripped_arg):
            if not news.is_enabled:
                news.enable()
            await news_cmd.finish('已开始新闻自动推送')
        else:
            if news.is_enabled:
                news.disable()
            await news_cmd.finish('已停止新闻自动推送')
    else:
        if news.is_enabled:
            await news_cmd.finish('新闻自动推送开启中')
        else:
            await news_cmd.finish('新闻自动推送关闭中')


#endregion
#region FFLogs
fflogs_cmd = ff14.command('dps', aliases={'dps'})

fflogs_cmd.__doc__ = """
dps

欢迎使用最终幻想XIV输出查询插件

查询输出排行榜：
/dps <副本名> <职业> <DPS种类>（支持 rdps adps pdps，留空默认为 rdps）
查询指定角色的排名：
/dps 副本名 角色名 服务器名
也可直接查询自己绑定角色的排名：
/dps 副本名 me
"""


@fflogs_cmd.handle()
async def handle_fflogs(bot: Bot, event: Event, state: dict):
    user_id = event.user_id
    argv = str(event.message).strip().split()

    if not argv:
        await fflogs_cmd.finish(fflogs_cmd.__doc__)

    # 设置 Token
    if argv[0] == 'token' and len(argv) == 2:
        # 检查是否是超级用户
        if user_id not in bot.config.superusers:
            await fflogs_cmd.finish('抱歉，你没有权限修改 Token。')

        config.fflogs_token = argv[1]
        await fflogs_cmd.finish('Token 设置完成。')

    # 检查 Token 是否设置
    if not config.fflogs_token:
        await fflogs_cmd.finish(
            '对不起，Token 未设置，无法查询数据。\n请先使用命令\n/dps token <token>\n配置好 Token 后再尝试查询数据。'
        )

    if argv[0] == 'token' and len(argv) == 1:
        # 检查是否是超级用户
        if user_id not in bot.config.superusers:
            await fflogs_cmd.finish('抱歉，你没有权限查看 Token。')
        await fflogs_cmd.finish(f'当前的 Token 为 {config.fflogs_token}')

    # 缓存相关设置
    if argv[0] == 'cache':
        # 检查是否是超级用户
        if user_id not in bot.config.superusers:
            await fflogs_cmd.finish('抱歉，你没有设置缓存。')
        if len(argv) == 2:
            if strtobool(argv[1]):
                if not fflogs.is_cache_enabled:
                    fflogs.enable_cache()
                await fflogs_cmd.finish('已开始定时缓存')
            else:
                if fflogs.is_cache_enabled:
                    fflogs.disable_cache()
                await fflogs_cmd.finish('已停止定时缓存')
        else:
            if fflogs.is_cache_enabled:
                await fflogs_cmd.finish('定时缓存开启中')
            else:
                await fflogs_cmd.finish('定时缓存关闭中')

    if argv[0] == 'me' and len(argv) == 1:
        if user_id not in fflogs.characters:
            await fflogs_cmd.finish(
                '抱歉，你没有绑定最终幻想14的角色。\n请使用\n/dps me <角色名> <服务器名>\n绑定自己的角色。'
            )
        await fflogs_cmd.finish(
            f'你当前绑定的角色：\n角色：{fflogs.characters[user_id][0]}\n服务器：{fflogs.characters[user_id][1]}'
        )

    if argv[0] == 'me' and len(argv) == 3:
        fflogs.set_character(user_id, argv[1], argv[2])
        await fflogs_cmd.finish('角色绑定成功！')

    if argv[0] == 'classes' and len(argv) == 1:
        reply = await fflogs.classes()
        await fflogs_cmd.finish(str(reply))

    if argv[0] == 'zones' and len(argv) == 2:
        reply = await fflogs.zones()
        await fflogs_cmd.finish(str(reply[int(argv[1])]))

    # 判断查询排行是指个人还是特定职业
    if len(argv) == 2:
        # <BOSS名> me
        # <BOSS名> <@他人>
        # <BOSS名> <职业名>
        if argv[1].lower() in ['me', 'i', '我']:
            reply = await get_character_dps_by_user_id(argv[0], user_id)
        elif '[CQ:at,qq=' in argv[1]:
            # @他人的格式
            # [CQ:at,qq=12345678]
            user_id = int(argv[1][10:-1])
            reply = await get_character_dps_by_user_id(argv[0], user_id)
        else:
            reply = await fflogs.dps(*argv)
        await fflogs_cmd.finish(reply)

    if len(argv) == 3:
        # <BOSS名> <职业名> <DPS种类>
        # <BOSS名> <角色名> <服务器名>
        if argv[2] in ['adps', 'rdps', 'pdps']:
            reply = await fflogs.dps(*argv)
        else:
            reply = await fflogs.character_dps(*argv)
        await fflogs_cmd.finish(reply)

    await fflogs_cmd.finish(fflogs_cmd.__doc__)


async def get_character_dps_by_user_id(boss_nickname: str, user_id: int):
    """ 通过 BOSS 名称和 QQ 号来获取角色的 DPS 数据 """
    if user_id not in fflogs.characters:
        return '抱歉，你没有绑定最终幻想14的角色。\n请使用\n/dps me <角色名> <服务器名>\n绑定自己的角色。'
    return await fflogs.character_dps(
        boss_nickname,
        *fflogs.characters[user_id],
    )


#endregion
