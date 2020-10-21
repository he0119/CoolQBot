""" 机器人插件
"""
from nonebot import on_message
from nonebot.adapters.cqhttp import escape
from nonebot.rule import to_me
from nonebot.typing import Bot, Event

from src.utils.helpers import render_expression

from .tencent import call_tencent_api
from .tuling import call_tuling_api

robot = on_message(rule=to_me(), priority=5, block=True)

# 定义无法获取机器人回复时的「表达（Expression）」
EXPR_DONT_UNDERSTAND = (
    '我现在还不太明白你在说什么呢，但没关系，以后的我会变得更强呢！',
    '我有点看不懂你的意思呀，可以跟我聊些简单的话题嘛',
    '其实我不太明白你的意思...',
    '抱歉哦，我现在的能力还不能够明白你在说什么，但我会加油的～'
) # yapf: disable


@robot.handle()
async def handle_robot(bot: Bot, event: Event, state: dict):
    args = str(event.message).strip()    # 首次发送命令时跟随的参数，例：/天气 上海，则args为上海
    if args:
        state['msg'] = args    # 如果用户发送了参数则直接赋值


@robot.got('msg')
async def handle_msg(bot: Bot, event: Event, state: dict):
    msg = state['msg']
    # 通过封装的函数获取机器人的回复
    reply = await call_tuling_api(event, msg)
    if reply:
        # 如果调用机器人成功，得到了回复，则转义之后发送给用户
        # 转义会把消息中的某些特殊字符做转换，以避免 酷Q 将它们理解为 CQ 码
        await robot.finish(escape(reply))

    reply = await call_tencent_api(event, msg)
    if reply:
        await robot.finish(escape(reply))

    # 如果调用失败，或者它返回的内容我们目前处理不了，发送无法获取回复时的「表达」
    # 这里的 render_expression() 函数会将一个「表达」渲染成一个字符串消息
    await robot.finish(render_expression(EXPR_DONT_UNDERSTAND))
