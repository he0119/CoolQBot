""" 词云
"""
from datetime import datetime, timedelta

from nonebot import CommandGroup, on_message
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.plugins.datastore import get_session

from .data import get_wordcloud
from .model import Message

wordcloud = CommandGroup("wordcloud")

# region 保存消息
save_message = on_message(permission=GROUP, priority=1)


@save_message.handle()
async def save_message_handle(
    event: GroupMessageEvent, session: AsyncSession = Depends(get_session)
):
    message = Message(
        time=event.time,  # type: ignore
        user_id=event.user_id,  # type: ignore
        group_id=event.group_id,  # type: ignore
        message=event.message.extract_plain_text(),
        platform="qq",
    )
    async with session:
        session.add(message)
        await session.commit()


# endregion

# region 词云
today_cmd = wordcloud.command("today", aliases={"今日词云", ("词云", "今日")})


@today_cmd.handle()
async def today_handle(
    event: GroupMessageEvent, session: AsyncSession = Depends(get_session)
):
    now = datetime.now()
    now = now.replace(hour=0, minute=0, second=0, microsecond=0)
    image = await get_wordcloud(
        session,
        str(event.group_id),
        start=now,
        end=now + timedelta(days=1),
    )
    if image:
        await today_cmd.finish(MessageSegment.image(image.tobytes()))
    else:
        await today_cmd.finish("今天没有足够的数据生成词云")


# endregion
