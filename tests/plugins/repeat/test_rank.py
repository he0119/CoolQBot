from datetime import date, datetime

import pytest
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebug import App
from pytest_mock import MockerFixture
from sqlalchemy.exc import IntegrityError

from tests.fake import fake_group_message_event_v11


@pytest.fixture
async def records(app: App, mocker: MockerFixture):
    from nonebot_plugin_datastore import create_session

    from src.plugins.repeat.models import Enabled, Record

    mocked_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
    mocked_datetime.now.return_value = datetime(2020, 1, 2)
    mocked_datetime.return_value = datetime(2020, 1, 1)

    async with create_session() as session:
        session.add(Enabled(platform="qq", group_id=10000))
        session.add(
            Record(
                date=date(2020, 1, 1),
                platform="qq",
                group_id=10000,
                user_id=10,
                msg_number=100,
                repeat_time=10,
            )
        )
        await session.commit()


async def test_unique_record(records: None):
    from nonebot_plugin_datastore import create_session

    from src.plugins.repeat.models import Record

    async with create_session() as session:
        session.add(
            Record(
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


async def test_rank(app: App, records: None):
    """测试排行榜"""
    from src.plugins.repeat.plugins.repeat_rank import rank_cmd

    async with app.test_matcher(rank_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/rank"))

        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_group_member_info",
            data={"group_id": 10000, "user_id": 10},
            result={"card": "test"},
        )
        ctx.should_call_send(
            event, "Love Love Ranking\ntest：10.00%\n\n复读次数排行榜\ntest：10次", True
        )
        ctx.should_finished()


async def test_rank_limit(app: App, records: None):
    """不限制最低次数"""
    from src.plugins.repeat.plugins.repeat_rank import rank_cmd

    async with app.test_matcher(rank_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
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
        ctx.should_finished()


async def test_rank_not_enabled(app: App):
    """没有启用复读的情况"""
    from src.plugins.repeat.plugins.repeat_rank import rank_cmd

    async with app.test_matcher(rank_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/rank"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "该群未开启复读功能，无法获取排行榜。", True)
        ctx.should_finished()
