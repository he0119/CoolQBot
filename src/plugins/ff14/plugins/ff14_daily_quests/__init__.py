""" 每日委托配对 """
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot_plugin_datastore import get_plugin_data
from nonebot_plugin_user import UserSession

from src.plugins.ff14 import ff14

from .data_source import get_daily_quests, get_daily_quests_pair, set_daily_quests

__plugin_meta__ = PluginMetadata(
    name="每日委托",
    description="查询与自己每日委托相同的群友",
    usage="""查看自己的每日委托
/每日委托
查询与自己每日委托相同的人
/每日委托 配对
记录每日委托
/每日委托 乐园都市笑笑镇, 伊弗利特歼灭战, 神龙歼灭战
""",
)

plugin_data = get_plugin_data()

daily_quests_cmd = ff14.command("daily_quests", aliases={"每日委托"})


@daily_quests_cmd.handle()
async def daily_quests_handle(session: UserSession, args: Message = CommandArg()):
    """每日委托"""
    content = args.extract_plain_text().strip()

    if not content:
        reply = get_daily_quests(session.user_id)
        await daily_quests_cmd.finish(reply)

    if content == "配对":
        reply = await get_daily_quests_pair(session.user_id)
        await daily_quests_cmd.finish(reply)
    else:
        quests = content.replace("，", ",").split(",")
        quests = [quest.strip() for quest in quests]
        set_daily_quests(session.user_id, quests)
        await daily_quests_cmd.finish("每日委托设置成功。")
