from datetime import datetime
from typing import TYPE_CHECKING

from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession


async def test_fitness_history(
    app: App, session: "AsyncSession", mocker: MockerFixture
):
    """测试健身历史记录"""
    from src.plugins.check_in.models import FitnessRecord
    from src.plugins.check_in.plugins.check_in_history import history_cmd

    session.add(FitnessRecord(user_id=1, time=datetime(2023, 1, 1), message="健身记录"))
    session.add(FitnessRecord(user_id=1, time=datetime(2023, 2, 1), message="健身记录"))
    session.add(FitnessRecord(user_id=2, message="健身记录"))
    await session.commit()

    mocked_datetime = mocker.patch(
        "src.plugins.check_in.plugins.check_in_history.datetime"
    )
    mocked_datetime.now.return_value = datetime(2023, 2, 10, 1, 1, 1)

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/打卡历史 健身"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "你已成功打卡 1 次，以下是你当月的健身情况哦～：\n2023-02-01 健身记录",
            True,
            at_sender=True,
        )
        ctx.should_finished(history_cmd)


async def test_dietary_history(app: App, session: "AsyncSession"):
    """测试饮食历史记录"""
    from src.plugins.check_in.models import DietaryRecord
    from src.plugins.check_in.plugins.check_in_history import history_cmd

    session.add(DietaryRecord(user_id=1, time=datetime(2023, 1, 1), healthy=True))
    session.add(DietaryRecord(user_id=1, time=datetime(2023, 1, 2), healthy=True))
    session.add(DietaryRecord(user_id=1, time=datetime(2023, 1, 3), healthy=False))
    session.add(DietaryRecord(user_id=2, healthy=True))
    await session.commit()

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/打卡历史 饮食"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "你已成功打卡 3 次，其中健康饮食 2 次，不健康饮食 1 次",
            True,
            at_sender=True,
        )
        ctx.should_finished(history_cmd)


async def test_weight_record_history(
    app: App, session: "AsyncSession", mocker: MockerFixture
):
    """测试体重历史记录"""
    from src.plugins.check_in.models import WeightRecord
    from src.plugins.check_in.plugins.check_in_history import history_cmd

    image_url = b"http://example.com"
    mocked_gerenate_graph = mocker.patch(
        "src.plugins.check_in.plugins.check_in_history.generate_graph",
        return_value=image_url,
    )

    session.add(WeightRecord(user_id=1, time=datetime(2023, 1, 1), weight=50))
    session.add(WeightRecord(user_id=1, time=datetime(2023, 1, 2), weight=51))
    session.add(WeightRecord(user_id=1, time=datetime(2023, 1, 3), weight=52))
    session.add(WeightRecord(user_id=2, weight=40))
    await session.commit()

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/打卡历史 体重"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.at(10)
            + MessageSegment.text("你的目标体重是 NaNkg\n")
            + MessageSegment.image(image_url),
            True,
        )
        ctx.should_finished(history_cmd)

    mocked_gerenate_graph.assert_called_once()


async def test_body_fat_record_history(
    app: App, session: "AsyncSession", mocker: MockerFixture
):
    """测试体脂历史记录"""
    from src.plugins.check_in.models import BodyFatRecord
    from src.plugins.check_in.plugins.check_in_history import history_cmd

    image_url = b"http://example.com"
    mocked_gerenate_graph = mocker.patch(
        "src.plugins.check_in.plugins.check_in_history.generate_graph",
        return_value=image_url,
    )

    session.add(BodyFatRecord(user_id=1, time=datetime(2023, 1, 1), body_fat=50))
    session.add(BodyFatRecord(user_id=1, time=datetime(2023, 1, 2), body_fat=51))
    session.add(BodyFatRecord(user_id=1, time=datetime(2023, 1, 3), body_fat=52))
    session.add(BodyFatRecord(user_id=2, body_fat=40))
    await session.commit()

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/打卡历史 体脂"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.at(10)
            + MessageSegment.text("你的目标体脂是 NaN%\n")
            + MessageSegment.image(image_url),
            True,
        )
        ctx.should_finished(history_cmd)

    mocked_gerenate_graph.assert_called_once()


async def test_history_other(app: App):
    """测试其他情况"""
    from src.plugins.check_in.plugins.check_in_history import (
        __plugin_meta__,
        history_cmd,
    )

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/打卡历史"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, __plugin_meta__.usage, True, at_sender=True)
        ctx.should_finished(history_cmd)

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/打卡历史 aa"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "不存在这项历史，请重新输入", True, at_sender=True)
        ctx.should_finished(history_cmd)

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/打卡历史 健身"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你还没有健身打卡记录哦", True, at_sender=True)
        ctx.should_finished(history_cmd)

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/打卡历史 饮食"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你还没有饮食打卡记录哦", True, at_sender=True)
        ctx.should_finished(history_cmd)

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/打卡历史 体重"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你还没有体重记录哦", True, at_sender=True)
        ctx.should_finished(history_cmd)

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/打卡历史 体脂"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你还没有体脂记录哦", True, at_sender=True)
        ctx.should_finished(history_cmd)
