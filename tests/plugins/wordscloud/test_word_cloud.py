from datetime import datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

import pytest
from nonebug import App
from pytest_mock import MockerFixture
from sqlmodel.ext.asyncio.session import AsyncSession

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.wordscloud",)], indirect=True)
async def test_word_cloud(
    app: App,
    session: AsyncSession,
    mocker: MockerFixture,
):
    """测试词云"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from src.plugins.wordscloud import Message as MessageModel
    from src.plugins.wordscloud import get_wordcloud, today_cmd

    now = datetime(2022, 1, 2, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    async with session:
        for word in ["你", "我", "他", "这是一句完整的话", "你知道吗？今天的天气真好呀！", "/今日词云"]:
            message = MessageModel(
                user_id="10",
                group_id="10000",
                message=word,
                time=datetime(2022, 1, 2, 4, 0, 0),
                platform="qq",
            )
            session.add(message)
        await session.commit()

    image = await get_wordcloud(
        session,
        "10000",
        start=now - timedelta(days=1),
        end=now,
    )

    assert image is not None
    assert image.size == (400, 200)

    mocked_datetime = mocker.patch("src.plugins.wordscloud.datetime")
    mocked_datetime.now.return_value = now
    mocked_get_wordcloud = mocker.patch("src.plugins.wordscloud.get_wordcloud")
    mocked_get_wordcloud.return_value = image
    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="PNG")

    async with app.test_matcher(today_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.image(img_byte_arr), "")
        ctx.should_finished()

    mocked_datetime.now.assert_called_once()
    assert mocked_get_wordcloud.call_args.kwargs == {
        "start": datetime(2022, 1, 1, 16, 0, 0, tzinfo=ZoneInfo("UTC")),
        "end": datetime(2022, 1, 2, 16, 0, 0, tzinfo=ZoneInfo("UTC")),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.wordscloud",)], indirect=True)
async def test_word_cloud_empty(app: App, session: AsyncSession):
    """测试词云，消息为空的情况"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.wordscloud import today_cmd

    async with app.test_matcher(today_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "今天没有足够的数据生成词云", "")
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.wordscloud",)], indirect=True)
async def test_word_cloud_empty_msg(
    app: App,
    session: AsyncSession,
    mocker: MockerFixture,
):
    """测试词云，消息均是 stopwords 的情况"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.wordscloud import Message as MessageModel
    from src.plugins.wordscloud import today_cmd

    now = datetime(2022, 1, 2, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    async with session:
        for word in ["你", "我", "他"]:
            message = MessageModel(
                user_id="10",
                group_id="10000",
                message=word,
                time=datetime(2022, 1, 2, 4, 0, 0),
                platform="qq",
            )
            session.add(message)
        await session.commit()

    mocked_datetime = mocker.patch("src.plugins.wordscloud.datetime")
    mocked_datetime.now.return_value = now

    async with app.test_matcher(today_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/今日词云"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "今天没有足够的数据生成词云", "")
        ctx.should_finished()
