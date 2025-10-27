from nonebot import get_driver, logger, require
from nonebot.adapters import Bot, Event
from nonebot.params import Depends
from nonebot.permission import Permission

require("nonebot_plugin_uninfo")
require("nonebot_plugin_user")
require("nonebot_plugin_alconna")
from arclet.alconna import Alconna
from nonebot_plugin_alconna import Extension, UniMessage
from nonebot_plugin_uninfo import get_session
from nonebot_plugin_user import User
from nonebot_plugin_user.utils import get_user

config = get_driver().config


async def is_superuser(user: User) -> bool:
    """检查当前用户是否属于超级管理员"""
    return user.name in config.superusers


class SuperUser:
    """检查当前事件是否属于超级管理员"""

    __slots__ = ()

    def __repr__(self) -> str:
        return "Superuser()"

    async def __call__(self, bot: Bot, event: Event) -> bool:
        session = await get_session(bot, event)
        if not session:
            return False
        user = await get_user(session.scope, session.user.id)
        return user.name in bot.config.superusers


SUPERUSER: Permission = Permission(is_superuser)
"""匹配任意超级用户事件"""


class SuperUserShortcutExtension(Extension):
    """用于设置仅超级用户可使用内置选项 --shortcut 的扩展"""

    @property
    def priority(self) -> int:
        return 20

    @property
    def id(self) -> str:
        return "nonebot_plugin_alisten.extensions:SuperUserShortcutExtension"

    async def receive_wrapper(self, bot: Bot, event: Event, command: Alconna, receive: UniMessage) -> UniMessage:
        superuser = await self.inject(Depends(is_superuser))
        if superuser:
            command.namespace_config.disable_builtin_options.discard("shortcut")
        else:
            command.namespace_config.disable_builtin_options.add("shortcut")
        return receive


def patch_permission():
    """替换权限系统中的 SuperUser

    替换为使用 nonebot-plugin-user 的 SuperUser
    """
    import nonebot.permission
    import nonebot_plugin_alconna.builtins.extensions.shortcut

    nonebot.permission.SuperUser = SuperUser
    nonebot.permission.SUPERUSER = SUPERUSER
    nonebot_plugin_alconna.builtins.extensions.shortcut.SuperUserShortcutExtension = SuperUserShortcutExtension

    logger.debug("替换权限系统中的 SuperUser 为使用 nonebot-plugin-user 的 SuperUser")
