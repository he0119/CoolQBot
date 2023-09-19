from typing import TYPE_CHECKING

from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot
from nonebug import App

from tests.fake import fake_group_message_event_v11

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio.session import AsyncSession


async def test_discharge(app: App, session: "AsyncSession"):
    """测试病人出院"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from src.plugins.cyber_hospital import discharge_cmd
    from src.plugins.cyber_hospital.model import Patient

    async with app.test_matcher(discharge_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/出院"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请 @ 需要出院的病人", True)
        ctx.should_finished(discharge_cmd)

    async with app.test_matcher(discharge_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/出院") + MessageSegment.at(10), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "未入院", True)
        ctx.should_finished(discharge_cmd)

    patient = Patient(user_id=1, group_id="qq_10000")
    session.add(patient)
    await session.commit()

    async with app.test_matcher(discharge_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/出院") + MessageSegment.at(10), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "出院成功", True)
        ctx.should_finished(discharge_cmd)

    async with app.test_matcher(discharge_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/出院") + MessageSegment.at(10), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "未入院", True)
        ctx.should_finished(discharge_cmd)
