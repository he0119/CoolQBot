from typing import TYPE_CHECKING

from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App

from tests.fake import fake_group_message_event_v11

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession


async def test_admin(app: App):
    """测试病人入院"""
    from src.plugins.cyber_hospital import admit_cmd

    async with app.test_matcher(admit_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/入院"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请 @ 需要入院的病人", True)
        ctx.should_finished(admit_cmd)

    async with app.test_matcher(admit_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/入院") + MessageSegment.at(123456),
            sender={"role": "admin"},
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "入院成功", True)
        ctx.should_finished(admit_cmd)

    async with app.test_matcher(admit_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/入院") + MessageSegment.at(123456),
            sender={"role": "admin"},
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "已入院", True)
        ctx.should_finished(admit_cmd)


async def test_admin_different_group(app: App, session: "AsyncSession"):
    """测试病人在不同群内入院"""

    from src.plugins.cyber_hospital import admit_cmd
    from src.plugins.cyber_hospital.model import Patient

    patient = Patient(user_id=2, group_id="qq-10001")
    session.add(patient)
    await session.commit()

    async with app.test_matcher(admit_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/入院") + MessageSegment.at(123456),
            sender={"role": "admin"},
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "入院成功", True)
        ctx.should_finished(admit_cmd)
