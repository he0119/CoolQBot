from typing import TYPE_CHECKING

import pytest
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebug import App

from tests.fake import fake_group_message_event_v11

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession


async def test_rounds(app: App, session: "AsyncSession"):
    """测试查房"""

    from src.plugins.cyber_hospital import rounds_cmd
    from src.plugins.cyber_hospital.model import Patient

    async with app.test_matcher(rounds_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/查房"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前没有住院病人", True)
        ctx.should_finished()

    patient = Patient(user_id="123456", group_id="10000")
    session.add(patient)
    await session.commit()

    async with app.test_matcher(rounds_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/查房") + MessageSegment.at(123456), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "请问你现在有什么不适吗？", True)
        ctx.should_rejected()

        event = fake_group_message_event_v11(message=Message("头疼"), user_id=123456)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "记录成功", True)
        ctx.should_finished()

    async with app.test_matcher(rounds_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/查房") + MessageSegment.at(123456) + " ",
            sender={"role": "admin"},
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "请问你现在有什么不适吗？", True)
        ctx.should_rejected()

        event = fake_group_message_event_v11(message=Message("头疼"), user_id=123456)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "记录成功", True)
        ctx.should_finished()

    async with app.test_matcher(rounds_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/查房") + MessageSegment.at(123456),
            sender={"role": "admin"},
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "请问你现在有什么不适吗？", True)
        ctx.should_rejected()

        event = fake_group_message_event_v11(
            message=" " + MessageSegment.at(123456), user_id=123456
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "症状不能为空，请重新输入", True)
        ctx.should_rejected()

        event = fake_group_message_event_v11(message=Message("头疼"), user_id=123456)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "记录成功", True)
        ctx.should_finished()


async def test_rounds_with_record(app: App, session: "AsyncSession"):
    """测试查房并录入病情"""
    from src.plugins.cyber_hospital import rounds_cmd
    from src.plugins.cyber_hospital.model import Patient

    patient = Patient(user_id="123456", group_id="10000")
    session.add(patient)
    await session.commit()

    async with app.test_matcher(rounds_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/查房")
            + MessageSegment.at(123456)
            + MessageSegment.text("咳嗽"),
            sender={"role": "admin"},
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "记录成功", True)
        ctx.should_finished()
