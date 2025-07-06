from datetime import datetime
from typing import TYPE_CHECKING

from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App

from tests.fake import fake_group_message_event_v11

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession


async def test_record(app: App, session: "AsyncSession"):
    """测试病历"""
    from src.plugins.cyber_hospital import record_cmd
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

    record = Record(patient=patient2, content="咳嗽")
    session.add(record)
    await session.commit()
    await session.refresh(record)

    message = f"{record.time:%Y-%m-%d %H:%M} {record.content}"

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/病历"), sender={"role": "admin"})
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请 @ 需要查看记录的病人", True)
        ctx.should_finished(record_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(
            message=Message("/病历") + MessageSegment.at("10"),
            sender={"role": "admin"},
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at("10") + f"\n{message}", True)
        ctx.should_finished(record_cmd)


async def test_record_empty(app: App, session: "AsyncSession"):
    """测试病历为空"""
    from src.plugins.cyber_hospital import record_cmd
    from src.plugins.cyber_hospital.model import Patient

    patient = Patient(user_id=1, group_id="qq_10000")
    session.add(patient)
    await session.commit()

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(
            message=Message("/病历") + MessageSegment.at("10"),
            sender={"role": "admin"},
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at("10") + "暂时没有记录", True)
        ctx.should_finished(record_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(
            message=Message("/病历") + MessageSegment.at(2),
            sender={"role": "admin"},
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(2) + "未入院", True)
        ctx.should_finished(record_cmd)
