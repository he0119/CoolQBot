from datetime import date, datetime

import pytest
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from pytest_mock import MockerFixture
from sqlalchemy.exc import IntegrityError

from tests.fake import fake_group_message_event_v11


@pytest.fixture
async def _records(app: App, mocker: MockerFixture):
    from nonebot_plugin_orm import get_session

    from src.plugins.repeat.models import Enabled, MessageRecord

    mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
    mocked_datetime.now.return_value = datetime(2020, 1, 2)
    mocked_datetime.return_value = datetime(2020, 1, 1)

    async with get_session() as session:
        session.add(Enabled(platform="qq", group_id=10000))
        session.add(
            MessageRecord(
                date=date(2020, 1, 1),
                platform="qq",
                group_id=10000,
                user_id=10,
                msg_number=100,
                repeat_time=10,
            )
        )
        await session.commit()


@pytest.mark.usefixtures("_records")
async def test_unique_record():
    from nonebot_plugin_orm import get_session

    from src.plugins.repeat.models import MessageRecord

    async with get_session() as session:
        session.add(
            MessageRecord(
                date=date(2020, 1, 1),
                platform="qq",
                group_id=10000,
                user_id=10,
                msg_number=100,
                repeat_time=10,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.usefixtures("_records")
async def test_rank(app: App):
    """测试排行榜"""
    from src.plugins.repeat.plugins.repeat_rank import rank_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/rank"))
        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10},
            result={"card": "test"},
        )
        ctx.should_call_send(event, "Love Love Ranking\ntest：10.00%\n\n复读次数排行榜\ntest：10次", True)
        ctx.should_finished(rank_cmd)


@pytest.mark.usefixtures("_records")
async def test_rank_limit(app: App):
    """不限制最低次数"""
    from src.plugins.repeat.plugins.repeat_rank import rank_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/rank n0"))
        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10},
            result={"card": "test"},
        )
        ctx.should_call_send(
            event,
            "Love Love Ranking\ntest(100)：10.00%\n\n复读次数排行榜\ntest(100)：10次",
            True,
        )
        ctx.should_finished(rank_cmd)


async def test_rank_not_enabled(app: App):
    """没有启用复读的情况"""
    from src.plugins.repeat.plugins.repeat_rank import rank_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/rank"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "该群未开启复读功能，无法获取排行榜。", True)
        ctx.should_finished(rank_cmd)
