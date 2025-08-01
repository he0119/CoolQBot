"""掷骰子"""

from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension

from .data_source import get_rand

__plugin_meta__ = PluginMetadata(
    name="掷骰子",
    description="获得一个点数或者概率",
    usage="""获得 0-100 的点数
/rand
获得一件事情的概率
/rand 今天捐钱的概率""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)

rand_cmd = on_alconna(
    Alconna(
        "rand",
        Args["input?#特定事件的概率", str],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    use_cmd_start=True,
    block=True,
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(),
    ],
)


@rand_cmd.handle()
async def rand_handle(input: Match[str]):
    if input.available:
        str_data = get_rand(input.result)
    else:
        str_data = get_rand("")
    await rand_cmd.finish(str_data, at_sender=True)
