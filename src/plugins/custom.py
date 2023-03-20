from typing import Any

from nonebot.adapters.onebot.v12 import Adapter, Bot, Event, Message, MessageSegment


async def send(
    bot: Bot,
    event: Event,
    message: str | Message | MessageSegment,
    at_sender: bool = False,
    reply_message: bool = False,
    **params: Any,
):
    """为了支持 QQ 频道"""
    event_dict = event.dict()

    params.setdefault("detail_type", event_dict["detail_type"])

    if "user_id" in event_dict:  # copy the user_id to the API params if exists
        params.setdefault("user_id", event_dict["user_id"])
    else:
        at_sender = False  # if no user_id, force disable at_sender

    if "group_id" in event_dict:  # copy the group_id to the API params if exists
        params.setdefault("group_id", event_dict["group_id"])

    if (
        "guild_id" in event_dict and "channel_id" in event_dict
    ):  # copy the guild_id to the API params if exists
        params.setdefault("guild_id", event_dict["guild_id"])
        params.setdefault("channel_id", event_dict["channel_id"])

    full_message = Message()  # create a new message with at sender segment
    if reply_message and "message_id" in event_dict:
        full_message += MessageSegment.reply(event_dict["message_id"])
    if at_sender and params["detail_type"] != "private":
        full_message += MessageSegment.mention(params["user_id"]) + " "
    full_message += message
    params.setdefault("message", full_message)

    # 传递 event_id，用来支持频道的被动消息
    params.setdefault("event_id", event_dict["id"])
    # 传递 guild_id，以支持私信
    if params["detail_type"] == "private":
        params.setdefault("guild_id", event_dict["qqguild"]["guild_id"])

    return await bot.send_message(**params)


# FIXME: 暂时反着写，因为适配器写反了，等发布新版之后改回来
# https://github.com/nonebot/adapter-onebot/commit/0e8dddc662c271b235d7d0ae4bc6f2312c675f75
Adapter.custom_send(send, impl="qqguild", platform="nonebot-plugin-all4one")
