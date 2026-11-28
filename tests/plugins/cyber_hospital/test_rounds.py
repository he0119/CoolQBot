from typing import TYPE_CHECKING

import pytest
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App
from sqlalchemy import select

from tests.fake import fake_group_message_event_v11

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession


@pytest.fixture
def second_group(monkeypatch: pytest.MonkeyPatch) -> int:
    from nonebot_plugin_uninfo import Member, Scene, SceneType, Session, User
    from nonebot_plugin_uninfo.adapters import INFO_FETCHER_MAPPING

    group_id = 10001
    cache = INFO_FETCHER_MAPPING["OneBot V11"].session_cache
    for user_id in ("10", "10000"):
        user = User(id=user_id, name=f"nickname{user_id}")
        monkeypatch.setitem(
            cache,
            f"group_{group_id}_{user_id}",
            Session(
                self_id="123456",
                adapter="OneBot V11",
                scope="QQClient",
                scene=Scene(id=str(group_id), type=SceneType.GROUP),
                user=user,
                member=Member(user=user),
            ),
        )
    return group_id


async def test_rounds(app: App, session: "AsyncSession"):
    """测试查房"""

    from src.plugins.cyber_hospital import rounds_cmd
    from src.plugins.cyber_hospital.model import Patient

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/查房"), sender={"role": "admin"})
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前没有住院病人", True)
        ctx.should_finished(rounds_cmd)

    patient = Patient(user_id=1, group_id="qq_10000")
    session.add(patient)
    await session.commit()

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/查房") + MessageSegment.at(10), sender={"role": "admin"})
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "请问你现在有什么不适吗？", True)
        ctx.should_rejected(rounds_cmd)

        event = fake_group_message_event_v11(message=Message("头疼"), user_id=10)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "记录成功", True)
        ctx.should_finished(rounds_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(
            message=Message("/查房") + MessageSegment.at(10) + " ",
            sender={"role": "admin"},
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "请问你现在有什么不适吗？", True)
        ctx.should_rejected(rounds_cmd)

        event = fake_group_message_event_v11(message=Message("头疼"), user_id=10)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "记录成功", True)
        ctx.should_finished(rounds_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(
            message=Message("/查房") + MessageSegment.at(10),
            sender={"role": "admin"},
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "请问你现在有什么不适吗？", True)
        ctx.should_rejected(rounds_cmd)

        event = fake_group_message_event_v11(message=" " + MessageSegment.at(10), user_id=10)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "症状不能为空，请重新输入", True)
        ctx.should_rejected(rounds_cmd)

        event = fake_group_message_event_v11(message=Message("头疼"), user_id=10)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "记录成功", True)
        ctx.should_finished(rounds_cmd)


async def test_rounds_with_record(app: App, session: "AsyncSession"):
    """测试查房并录入病情"""
    from src.plugins.cyber_hospital import rounds_cmd
    from src.plugins.cyber_hospital.model import Patient

    patient = Patient(user_id=1, group_id="qq_10000")
    session.add(patient)
    await session.commit()

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(
            message=Message("/查房") + MessageSegment.at(10) + MessageSegment.text("咳嗽"),
            sender={"role": "admin"},
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "记录成功", True)
        ctx.should_finished(rounds_cmd)


@pytest.mark.parametrize("content", ["", "咳嗽"], ids=["prompt", "inline"])
async def test_rounds_requires_admission_in_origin_group(
    app: App, session: "AsyncSession", second_group: int, content: str
):
    from nonebot_plugin_user import get_user

    from src.plugins.cyber_hospital import rounds_cmd
    from src.plugins.cyber_hospital.model import Patient, Record

    patient = await get_user("QQClient", "10")
    session.add(Patient(user_id=patient.id, group_id="qq_10000"))
    await session.commit()

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        event = fake_group_message_event_v11(
            message=Message("/查房") + MessageSegment.at(10) + content,
            sender={"role": "admin"},
            user_id=10000,
            group_id=second_group,
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + " 未入院", True)
        ctx.should_finished(rounds_cmd)

    assert (await session.scalars(select(Record))).all() == []


@pytest.mark.parametrize("origin_admitted_first", [True, False], ids=["origin-first", "other-first"])
async def test_rounds_only_records_in_origin_group(
    app: App, session: "AsyncSession", second_group: int, origin_admitted_first: bool
):
    from nonebot_plugin_user import get_user

    from src.plugins.cyber_hospital import rounds_cmd
    from src.plugins.cyber_hospital.model import Patient, Record

    patient = await get_user("QQClient", "10")
    origin = Patient(user_id=patient.id, group_id=f"qq_{second_group}")
    other = Patient(user_id=patient.id, group_id="qq_10000")
    session.add_all([origin, other] if origin_admitted_first else [other, origin])
    await session.flush()
    origin_id = origin.id
    await session.commit()

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        inline = fake_group_message_event_v11(
            message=Message("/查房") + MessageSegment.at(10) + "咳嗽",
            sender={"role": "admin"},
            user_id=10000,
            group_id=second_group,
        )
        ctx.receive_event(bot, inline)
        ctx.should_call_send(inline, MessageSegment.at(10) + "记录成功", True)
        ctx.should_finished(rounds_cmd)

        prompt = fake_group_message_event_v11(
            message=Message("/查房") + MessageSegment.at(10),
            sender={"role": "admin"},
            user_id=10000,
            group_id=second_group,
        )
        ctx.receive_event(bot, prompt)
        ctx.should_call_send(prompt, MessageSegment.at(10) + "请问你现在有什么不适吗？", True)
        ctx.should_rejected(rounds_cmd)

        reply = fake_group_message_event_v11(message=Message("头疼"), user_id=10, group_id=second_group)
        ctx.receive_event(bot, reply)
        ctx.should_call_send(reply, MessageSegment.at(10) + "记录成功", True)
        ctx.should_finished(rounds_cmd)

    records = (await session.scalars(select(Record).order_by(Record.id))).all()
    assert [(record.patient_id, record.content) for record in records] == [(origin_id, "咳嗽"), (origin_id, "头疼")]


@pytest.mark.parametrize("readmit", [False, True], ids=["discharged", "readmitted"])
async def test_pending_rounds_does_not_write_after_discharge(
    app: App, session: "AsyncSession", second_group: int, readmit: bool
):
    from nonebot_plugin_user import get_user

    from src.plugins.cyber_hospital import admit_cmd, discharge_cmd, rounds_cmd
    from src.plugins.cyber_hospital.model import Patient, Record

    patient = await get_user("QQClient", "10")
    session.add_all(
        [Patient(user_id=patient.id, group_id="qq_10000"), Patient(user_id=patient.id, group_id=f"qq_{second_group}")]
    )
    await session.commit()

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        prompt = fake_group_message_event_v11(
            message=Message("/查房") + MessageSegment.at(10), sender={"role": "admin"}, user_id=10000
        )
        ctx.receive_event(bot, prompt)
        ctx.should_call_send(prompt, MessageSegment.at(10) + "请问你现在有什么不适吗？", True)
        ctx.should_rejected(rounds_cmd)

        discharge = fake_group_message_event_v11(
            message=Message("/出院") + MessageSegment.at(10), sender={"role": "admin"}, user_id=10000
        )
        ctx.receive_event(bot, discharge)
        ctx.should_call_send(discharge, MessageSegment.at(10) + "出院成功", True)
        ctx.should_finished(discharge_cmd)

        if readmit:
            admit = fake_group_message_event_v11(
                message=Message("/入院") + MessageSegment.at(10), sender={"role": "admin"}, user_id=10000
            )
            ctx.receive_event(bot, admit)
            ctx.should_call_send(admit, MessageSegment.at(10) + "入院成功", True)
            ctx.should_finished(admit_cmd)

        reply = fake_group_message_event_v11(message=Message("头疼"), user_id=10)
        ctx.receive_event(bot, reply)
        ctx.should_call_send(reply, MessageSegment.at(10) + " 未入院", True)
        ctx.should_finished(rounds_cmd)

    assert (await session.scalars(select(Record))).all() == []
