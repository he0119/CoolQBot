from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from nonebug import App

from tests.fake import fake_group_message_event_v11

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession


@pytest.mark.parametrize("app", [("src.plugins.hospital",)], indirect=True)
async def test_history(app: App, session: "AsyncSession"):
    """测试入院记录"""
    from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment

    from src.plugins.hospital import history_cmd
    from src.plugins.hospital.model import Patient, Record

    patient = Patient(
        user_id="123456",
        group_id="10000",
        admitted_at=datetime.now(),
        discharged_at=datetime.now(),
    )
    patient2 = Patient(user_id="123456", group_id="10000")
    patient3 = Patient(user_id="123", group_id="10000")
    patient4 = Patient(user_id="123456", group_id="10001")
    session.add(patient)
    session.add(patient2)
    session.add(patient3)
    session.add(patient4)
    await session.commit()

    await session.refresh(patient)
    await session.refresh(patient2)

    message = f"入院时间：{patient.admitted_at:%Y-%m-%d %H:%M} 出院时间：{patient.discharged_at:%Y-%m-%d %H:%M}\n入院时间：{patient2.admitted_at:%Y-%m-%d %H:%M} 出院时间：未出院"

    record = Record(patient=patient2, content="咳嗽")
    session.add(record)
    await session.commit()

    async with app.test_matcher(history_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/入院记录"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_api(
            "get_group_member_info",
            {"group_id": 10000, "user_id": 123},
            {"card": "1"},
        )
        ctx.should_call_api(
            "get_group_member_info",
            {"group_id": 10000, "user_id": 123456},
            {"card": "2"},
        )
        ctx.should_call_send(event, "1 入院次数：1\n2 入院次数：2", True)
        ctx.should_finished()

    async with app.test_matcher(history_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/入院记录") + MessageSegment.at("123456"),
            sender={"role": "admin"},
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.at("123456") + message,
            True,
        )
        ctx.should_finished()

    async with app.test_matcher(history_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/入院记录") + MessageSegment.at("1"),
            sender={"role": "admin"},
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.at("1") + "从未入院",
            True,
        )
        ctx.should_finished()


@pytest.mark.parametrize("app", [("src.plugins.hospital",)], indirect=True)
async def test_history_empty(app: App, session: "AsyncSession"):
    """测试入院记录为空"""
    from nonebot.adapters.onebot.v11 import Bot, Message

    from src.plugins.hospital import history_cmd

    async with app.test_matcher(history_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/入院记录"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有住院病人", True)
        ctx.should_finished()
