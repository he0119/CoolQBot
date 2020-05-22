import re

from nonebot import IntentCommand, NLPSession, on_natural_language, permission


@on_natural_language(only_to_me=False, permission=permission.GROUP)
async def _(session: NLPSession):
    # 只复读群消息，与没有对机器人说的话
    if not session.event['to_me']:
        # 以置信度 60.0 返回 repeat 命令
        # 确保任何消息都在且仅在其它自然语言处理器无法理解的时候使用 repeat 命令
        return IntentCommand(
            60.0, ('repeat', 'group'), args={'message': session.msg}
        )


@on_natural_language(only_to_me=False)
async def _(session: NLPSession):
    match = re.match(r'^\[CQ:sign(.+)\]$', session.msg)
    if match:
        return IntentCommand(
            90.0, ('repeat', 'sign'), args={'message': session.msg}
        )


@on_natural_language(only_to_me=False)
async def _(session: NLPSession):
    """ 复读小程序

    将小程序转换为电脑可以打开的网址
    """
    match = re.match(r'^\[CQ:rich(.+)\]$', session.msg)
    if match:
        return IntentCommand(90.0, ('repeat', 'mina'))
