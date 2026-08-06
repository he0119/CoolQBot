"""大模型入口的共用匹配规则。"""

import nonebot
from nonebot.adapters import Bot, Event
from nonebot.rule import Rule, to_me
from nonebot.typing import T_State
from nonebot_plugin_uninfo import Uninfo

from .config import plugin_config


async def is_non_private(session: Uninfo) -> bool:
    """拒绝私聊，允许群聊、频道和子频道事件。"""
    return not session.scene.is_private


NON_PRIVATE_RULE = Rule(is_non_private)
_TO_ME_RULE = to_me()


async def should_handle_mention(bot: Bot, event: Event, state: T_State) -> bool:
    """按配置启用快捷对话，并避免带非空前缀的命令被重复处理。"""
    if not plugin_config.respond_to_mention or event.get_type() != "message":
        return False
    if not await _TO_ME_RULE(bot, event, state):
        return False
    try:
        text = event.get_plaintext().lstrip()
    except (NotImplementedError, ValueError):
        return False
    if any(prefix and text.startswith(prefix) for prefix in nonebot.get_driver().config.command_start):
        return False
    return await NON_PRIVATE_RULE(bot, event, state)


MENTION_RULE = Rule(should_handle_mention)
