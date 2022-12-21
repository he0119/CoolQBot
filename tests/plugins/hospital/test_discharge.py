import pytest
from nonebug import App
from sqlmodel.ext.asyncio.session import AsyncSession

from tests.fake import fake_group_message_event


@pytest.mark.skip(reason="sqlalchemy.exc.InvalidRequestError")
@pytest.mark.parametrize("app", [("src.plugins.hospital",)], indirect=True)
async def test_discharge(app: App, session: AsyncSession):
    """测试病人出院"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from src.plugins.hospital import discharge_cmd
    from src.plugins.hospital.model import Patient

    async with app.test_matcher(discharge_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
            message=Message("/出院"), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请 @ 需要出院的病人", True)
        ctx.should_finished()

    async with app.test_matcher(discharge_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
            message=Message("/出院") + MessageSegment.at(123456), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "未入院", True)
        ctx.should_finished()

    patient = Patient(user_id="123456", group_id="10000")
    session.add(patient)
    await session.commit()

    async with app.test_matcher(discharge_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
            message=Message("/出院") + MessageSegment.at(123456), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "出院成功", True)
        ctx.should_finished()

    async with app.test_matcher(discharge_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(
            message=Message("/出院") + MessageSegment.at(123456), sender={"role": "admin"}
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(123456) + "未入院", True)
        ctx.should_finished()
