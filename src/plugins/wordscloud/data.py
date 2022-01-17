from pathlib import Path

import jieba
from PIL.Image import Image
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from wordcloud import WordCloud

from .model import Message

font_path = Path(__file__).parent / "SimHei.ttf"


async def get_wordcloud(session: AsyncSession, group_id: str) -> Image:
    words = []
    async with session:
        statement = select(Message).where(Message.group_id == group_id)
        msg: list[Message] = (await session.exec(statement)).all()  # type: ignore
        msgs = " ".join([m.message for m in msg])
        words = jieba.lcut(msgs, cut_all=True)

    txt = " ".join(words)
    wordcloud = WordCloud(font_path=str(font_path)).generate(txt)
    image = wordcloud.to_image()
    return image
