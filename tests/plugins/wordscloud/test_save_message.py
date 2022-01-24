import pytest
from nonebug import App
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.wordscloud",)], indirect=True)
async def test_save_message(app: App, session: AsyncSession):
    """测试保存数据"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.wordscloud import Message as MessageModel
    from src.plugins.wordscloud import save_message

    async with app.test_matcher(save_message) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("今天的天气真好呀"))

        ctx.receive_event(bot, event)

    statement = select(MessageModel).limit(1)
    m = (await session.exec(statement)).first()  # type: ignore
    assert m.message == "今天的天气真好呀"  # type: ignore
