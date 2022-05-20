""" 机器人插件
"""
from nonebot import on_message
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.rule import Rule, to_me

from src.utils.helpers import render_expression

from .config import global_config
from .tencent import call_tencent_api


async def robot_rule(event: MessageEvent) -> bool:
    msg = event.get_plaintext()

    # 如果消息是命令，则忽略
    command_start = tuple(global_config.command_start)
    if msg.startswith(command_start):
        return False

    return True


robot_message = on_message(rule=to_me() & Rule(robot_rule), priority=5, block=True)

# 无法获取机器人回复时的表达
EXPR_DONT_UNDERSTAND = (
    "我现在还不太明白你在说什么呢，但没关系，以后的我会变得更强呢！",
    "我有点看不懂你的意思呀，可以跟我聊些简单的话题嘛",
    "其实我不太明白你的意思...",
    "抱歉哦，我现在的能力还不能够明白你在说什么，但我会加油的～",
)


@robot_message.handle()
async def robot_handle(event: MessageEvent):
    msg = event.get_plaintext()

    # 通过封装的函数获取机器人的回复
    reply = await call_tencent_api(msg)
    if reply:
        await robot_message.finish(reply)

    # 如果调用失败，或者它返回的内容我们目前处理不了，发送无法获取回复时的「表达」
    # 这里的 render_expression() 函数会将一个「表达」渲染成一个字符串消息
    await robot_message.finish(render_expression(EXPR_DONT_UNDERSTAND))
