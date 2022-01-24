""" 词云
"""
from datetime import datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

from nonebot import CommandGroup, on_message
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import Depends
from nonebot_plugin_datastore import get_session
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

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
    session.add(message)
    await session.commit()


# endregion

# region 词云
today_cmd = wordcloud.command("today", aliases={"今日词云", ("词云", "今日")})
today_cmd.__doc__ = """
词云

获取今天的词云
/今日词云
"""


@today_cmd.handle()
async def today_handle(
    event: GroupMessageEvent, session: AsyncSession = Depends(get_session)
):
    # 获取中国本地时间
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    now = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 中国时区差了 8 小时
    statement = select(Message).where(
        Message.group_id == str(event.group_id),
        Message.time >= now.astimezone(ZoneInfo("UTC")),
        Message.time <= (now + timedelta(days=1)).astimezone(ZoneInfo("UTC")),
    )
    messages: list[Message] = (await session.exec(statement)).all()  # type: ignore

    image = await get_wordcloud(messages)
    if image:
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        await today_cmd.finish(MessageSegment.image(image_bytes))
    else:
        await today_cmd.finish("今天没有足够的数据生成词云")


# endregion
