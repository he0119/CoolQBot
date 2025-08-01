"""查价"""

import httpx
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, MultiVar, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_datastore import get_plugin_data
from nonebot_plugin_user import UserSession

from .data_source import get_item_price

__plugin_meta__ = PluginMetadata(
    name="查价",
    description="查询服务器中的价格",
    usage="""查询大区中的最低价格
/查价 萨维奈舞裙 猫小胖
查询服务器中的最低价格
/查价 萨维奈舞裙 静语庄园
设置默认查询的区域
/查价 默认值 静语庄园
查询当前设置的默认值
/查价 默认值""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)

plugin_data = get_plugin_data()

price_cmd = on_alconna(
    Alconna(
        "price",
        Args["argv", MultiVar(str, flag="*")],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"查价"},
    use_cmd_start=True,
    block=True,
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "查价"}),
    ],
)


@price_cmd.handle()
async def price_handle(session: UserSession, argv: tuple[str, ...]):
    """查价"""
    user_id = session.user_id

    if len(argv) == 0:
        await price_cmd.finish(f"最终幻想XIV 价格查询\n\n{__plugin_meta__.usage}")

    if len(argv) == 1 and argv[0] == "默认值":
        world_or_dc = await plugin_data.config.get(f"default-{user_id}", "猫小胖")
        await price_cmd.finish(f"当前设置的默认值为：{world_or_dc}")

    if len(argv) == 2 and argv[0] == "默认值":
        await plugin_data.config.set(f"default-{user_id}", argv[1])
        await price_cmd.finish("查询区域默认值设置成功！")

    if len(argv) > 0:
        name = argv[0]
        if len(argv) >= 2:
            world_or_dc = argv[1]
        else:
            world_or_dc = await plugin_data.config.get(f"default-{user_id}", "猫小胖")

        try:
            reply = await get_item_price(name, world_or_dc)
        except httpx.HTTPError:
            reply = "抱歉，网络出错，无法获取物品价格，请稍后再试。"

        await price_cmd.finish(reply)
