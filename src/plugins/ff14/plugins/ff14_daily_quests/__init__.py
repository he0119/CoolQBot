"""每日委托配对"""

from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import (
    Alconna,
    Args,
    CommandMeta,
    Match,
    MultiVar,
    on_alconna,
)
from nonebot_plugin_datastore import get_plugin_data
from nonebot_plugin_user import UserSession

from .data_source import (
    get_daily_quests_overview,
    get_daily_quests_pair,
    set_daily_quests,
)

__plugin_meta__ = PluginMetadata(
    name="每日委托",
    description="查询与自己每日委托相同的群友",
    usage="""查询与自己每日委托相同的人
/每日委托
记录每日委托，并查看与自己每日委托相同的人
/每日委托 乐园都市笑笑镇, 伊弗利特歼灭战, 神龙歼灭战
查看今日所有委托
/每日委托 总览
""",
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna", "nonebot_plugin_user"
    ),
)

plugin_data = get_plugin_data()

daily_quests_cmd = on_alconna(
    Alconna(
        "每日委托",
        Args["quests?#委托（用逗号分隔）", MultiVar(str, "+")] / (",", "，"),
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"daily_quests"},
    use_cmd_start=True,
    block=True,
)


@daily_quests_cmd.handle()
async def daily_quests_handle(session: UserSession, quests: Match[tuple[str, ...]]):
    """每日委托"""
    if not quests.available:
        reply = await get_daily_quests_pair(session.user_id)
    elif quests.result == ("总览",):
        reply = await get_daily_quests_overview()
    else:
        set_daily_quests(session.user_id, list(quests.result))
        reply = await get_daily_quests_pair(session.user_id)

    await daily_quests_cmd.finish(reply, at_sender=True)
