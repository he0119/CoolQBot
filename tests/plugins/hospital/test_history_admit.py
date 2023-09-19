from datetime import datetime
from typing import TYPE_CHECKING

from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App

from tests.fake import fake_group_message_event_v11

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession


async def test_history(app: App, session: "AsyncSession"):
    """测试入院记录"""
    from src.plugins.cyber_hospital import history_cmd
    from src.plugins.cyber_hospital.model import Patient, Record

    patient = Patient(
        user_id=1,
        group_id="qq_10000",
        admitted_at=datetime.now(),
        discharged_at=datetime.now(),
    )
    patient2 = Patient(user_id=1, group_id="qq_10000")
    patient3 = Patient(user_id=2, group_id="qq_10000")
    patient4 = Patient(user_id=1, group_id="qq_10001")
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
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/入院记录"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "nickname 入院次数：2\nnickname10000 入院次数：1", True)
        ctx.should_finished(history_cmd)

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/入院记录") + MessageSegment.at("10"),
            sender={"role": "admin"},
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.at("10") + message,
            True,
        )
        ctx.should_finished(history_cmd)

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
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
        ctx.should_finished(history_cmd)


async def test_history_empty(app: App, session: "AsyncSession"):
    """测试入院记录为空"""
    from src.plugins.cyber_hospital import history_cmd

    async with app.test_matcher(history_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/入院记录"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有住院病人", True)
        ctx.should_finished(history_cmd)
