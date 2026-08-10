"""随机美食推荐插件。"""

import re

from nonebot import require
from nonebot.adapters import Bot, Event
from nonebot.log import logger
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_localstore")
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Image, MultiVar, Subcommand, Text, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension

from src.utils.helpers import admin_permission
from src.utils.remote_data import RemoteDataError

from .data_source import FOODS_DATA, recommend_food
from .image_api import get_food_image

__plugin_meta__ = PluginMetadata(
    name="吃什么",
    description="随机推荐一种美食",
    usage="""随机推荐一种美食
/吃什么
/what_to_eat（Telegram）
吃啥？
今晚吃什么
今天 中午吃啥？
管理员更新美食数据：/吃什么 update 或 /what_to_eat update""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)

what_to_eat_cmd = on_alconna(
    Alconna(
        "what_to_eat",
        Subcommand("update", help_text="更新美食数据（仅管理员）"),
        Args["context?#场景", MultiVar(str, flag="+")],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"吃什么"},
    use_cmd_start=True,
    block=True,
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "吃什么"}),
    ],
)

_command_prefix = next((prefix for prefix in what_to_eat_cmd.command().prefixes if isinstance(prefix, str)), "")
what_to_eat_cmd.shortcut(
    re.compile(r"(?P<context>.*?)吃(?:啥|什么)[?？]?"),
    command=f"{_command_prefix}what_to_eat",
    arguments=["{context}"],
    fuzzy=False,
    compact=False,
    humanized="xxxx吃啥 / xxxx吃什么",
)


@what_to_eat_cmd.assign("$main")
async def what_to_eat_handle():
    food = await recommend_food()
    text = f"推荐你吃：{food.name}！"
    image = await get_food_image(food.commons_file)
    if not image:
        await what_to_eat_cmd.finish(text, at_sender=True)

    message = Text(f"{text}\n") + Image(raw=image.content, mimetype=image.mimetype)
    message += Text(f"\n{image.attribution}")
    await what_to_eat_cmd.finish(message, at_sender=True)


@what_to_eat_cmd.assign("update")
async def what_to_eat_update_handle(bot: Bot, event: Event):
    """由管理员手动拉取 Pages 上的最新美食数据。"""
    if not await admin_permission()(bot, event):
        await what_to_eat_cmd.finish("该指令仅管理员可用", at_sender=True)

    try:
        dataset = await FOODS_DATA.update()
    except RemoteDataError as e:
        logger.warning("美食数据更新失败: {}", e)
        await what_to_eat_cmd.finish("美食数据更新失败，已保留原缓存", at_sender=True)
    await what_to_eat_cmd.finish(f"美食数据更新成功，数据日期：{dataset.version.isoformat()}", at_sender=True)
