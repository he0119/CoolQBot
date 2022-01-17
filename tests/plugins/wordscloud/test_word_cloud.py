from datetime import datetime
from pathlib import Path

import pytest
from nonebug import App
from PIL import Image, ImageChops
from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.wordscloud",)], indirect=True)
async def test_word_cloud(app: App, session: AsyncSession):
    """测试词云"""
    from src.plugins.wordscloud import Message as MessageModel
    from src.plugins.wordscloud import get_wordcloud

    async with session:
        for word in ["你", "我", "他", "他"]:
            message = MessageModel(
                user_id="10",
                group_id="10000",
                message=word,
                time=datetime.now(),
                platform="qq",
            )
            session.add(message)
        await session.commit()

    path = Path(__file__).parent / "ref.png"

    image = await get_wordcloud(session, "10000")

    assert image.size == (400, 200)
