""" 词云
"""

from nonebot import on_message
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.plugins.datastore import get_session

from .model import Message

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
    )
    async with session:
        session.add(message)
        await session.commit()
