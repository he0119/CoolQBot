from distutils.util import strtobool

from nonebot import CommandSession
from nonebot.permission import IS_SUPERUSER, check_permission

from . import cg
from .news import news


@cg.command(
    'ff14',
    aliases=['ff14', '最终幻想14', '最终幻想XIV'],
    only_to_me=False,
    shell_like=True
)
async def ff14(session: CommandSession):
    """ 最终幻想XIV
    """
    if len(session.argv) == 1 and session.argv[0] == 'news':
        if news.is_enabled:
            session.finish('新闻自动推送开启中')
        else:
            session.finish('新闻自动推送关闭中')
    if len(session.argv) == 2 and session.argv[0] == 'news':
        # 检查是否是超级用户
        if not await check_permission(
            session.bot, session.event, IS_SUPERUSER
        ):
            session.finish('我才不要听你的呢。')
        if strtobool(session.argv[1]):
            if not news.is_enabled:
                news.enable()
            session.finish('已开始新闻自动推送')
        else:
            if news.is_enabled:
                news.disable()
            session.finish('已停止新闻自动推送')

    session.finish('抱歉，并没有这个用法。')
