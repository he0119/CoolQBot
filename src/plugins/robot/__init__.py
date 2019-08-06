""" 机器人插件
"""
from aiocqhttp.message import escape
from nonebot import (CommandSession, IntentCommand, NLPSession, on_command,
                     on_natural_language)
from nonebot.helpers import render_expression

from .qingyunke import call_qingyunke_api
from .tuling import call_tuling_api

# 定义无法获取机器人回复时的「表达（Expression）」
EXPR_DONT_UNDERSTAND = ('我现在还不太明白你在说什么呢，但没关系，以后的我会变得更强呢！',
                        '我有点看不懂你的意思呀，可以跟我聊些简单的话题嘛', '其实我不太明白你的意思……',
                        '抱歉哦，我现在的能力还不能够明白你在说什么，但我会加油的～')


# 注册一个仅内部使用的命令，不需要 aliases
@on_command('robot')
async def robot(session: CommandSession):
    # 获取可选参数，这里如果没有 message 参数，命令不会被中断，message 变量会是 None
    message = session.state.get('message')

    # 通过封装的函数获取机器人的回复
    reply = await call_tuling_api(session, message)
    if reply:
        # 如果调用机器人成功，得到了回复，则转义之后发送给用户
        # 转义会把消息中的某些特殊字符做转换，以避免 酷Q 将它们理解为 CQ 码
        await session.send(escape(reply), at_sender=True)
        return

    reply = await call_qingyunke_api(session, message)
    if reply:
        await session.send(escape(reply), at_sender=True)
        return

    # 如果调用失败，或者它返回的内容我们目前处理不了，发送无法获取回复时的「表达」
    # 这里的 render_expression() 函数会将一个「表达」渲染成一个字符串消息
    await session.send(render_expression(EXPR_DONT_UNDERSTAND), at_sender=True)


@on_natural_language(only_short_message=False)
async def _(session: NLPSession):
    # 以置信度 60.0 返回 robot 命令
    # 确保任何消息都在且仅在其它自然语言处理器无法理解的时候使用 robot 命令
    return IntentCommand(60.0, 'robot', args={'message': session.msg_text})
