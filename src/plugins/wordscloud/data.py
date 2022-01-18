from datetime import datetime
from pathlib import Path
from typing import Optional

import jieba
from PIL.Image import Image
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from wordcloud import WordCloud

from .model import Message

font_path = Path(__file__).parent / "SimHei.ttf"
stopwords_path = Path(__file__).parent / "stopwords.txt"
with stopwords_path.open("r", encoding="utf8") as f:
    stopwords = [word.strip() for word in f.readlines()]


async def get_wordcloud(
    session: AsyncSession, group_id: str, start: datetime, end: datetime
) -> Optional[Image]:
    words = []
    async with session:
        statement = select(Message).where(
            Message.group_id == group_id,
            Message.time >= start,
            Message.time <= end,
        )
        msg: list[Message] = (await session.exec(statement)).all()  # type: ignore
        # 过滤掉命令
        msgs = " ".join([m.message for m in msg if not m.message.startswith("/")])
        # 分词
        words = jieba.lcut(msgs, cut_all=True)
        txt = "\n".join(words)
        try:
            wordcloud = WordCloud(font_path=str(font_path), stopwords=stopwords)
            image = wordcloud.generate(txt).to_image()
            return image
        except ValueError:
            pass
