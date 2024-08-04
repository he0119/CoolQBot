from datetime import datetime

import pytest
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


@pytest.fixture()
async def _records(app: App):
    from nonebot_plugin_orm import get_session

    from src.plugins.repeat.models import Enabled

    async with get_session() as session:
        session.add(Enabled(platform="qq", group_id="10000"))
        await session.commit()


@pytest.mark.usefixtures("_records")
async def test_repeat(app: App, mocker: MockerFixture):
    """测试复读"""
    from src.plugins.repeat.plugins.repeat_basic import repeat_message

    mocked_rule_datetime = mocker.patch(
        "src.plugins.repeat.plugins.repeat_basic.repeat_rule.datetime"
    )
    mocked_rule_datetime.now.return_value = datetime(2021, 1, 1, 0, 0, 0)
    mocked_recorder_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
    mocked_recorder_datetime.now.side_effect = [
        datetime(2020, 1, 1, 0, 0, 0),  # init
        datetime(2021, 1, 1, 1, 0, 0),  # add_repeat_list
        datetime(2021, 1, 1, 2, 0, 0),  # reset_last_message_on
    ]
    mocked_random = mocker.patch(
        "src.plugins.repeat.plugins.repeat_basic.repeat_rule.secrets.SystemRandom"
    )
    mocked_random().randint.return_value = 1

    async with app.test_matcher(repeat_message) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("123"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, event.message, None)
        ctx.should_finished(repeat_message)

    assert mocked_recorder_datetime.now.call_count == 3


@pytest.mark.usefixtures("_records")
async def test_repeat_enabled(app: App):
    """测试复读已开启的情况"""
    from src.plugins.repeat.plugins.repeat_basic import repeat_cmd

    async with app.test_matcher(repeat_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/repeat"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "复读功能开启中", None)
        ctx.should_finished(repeat_cmd)


async def test_repeat_not_enabled(app: App):
    """测试复读关闭的情况"""
    from src.plugins.repeat.plugins.repeat_basic import repeat_cmd

    async with app.test_matcher(repeat_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/repeat"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "复读功能关闭中", None)
        ctx.should_finished(repeat_cmd)


async def test_repeat_enable(app: App):
    """测试复读，在群里启用的情况"""
    from src.plugins.repeat.plugins.repeat_basic import repeat_cmd

    async with app.test_matcher(repeat_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/repeat 1"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群开启复读功能", None)
        ctx.should_finished(repeat_cmd)


@pytest.mark.usefixtures("_records")
async def test_repeat_disable(app: App):
    """测试复读，在群里关闭的情况"""
    from src.plugins.repeat.plugins.repeat_basic import repeat_cmd

    async with app.test_matcher(repeat_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/repeat 0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群关闭复读功能", None)
        ctx.should_finished(repeat_cmd)


async def test_repeat_disable_already_disabled(app: App):
    """测试复读，群里已关闭的情况"""
    from src.plugins.repeat.plugins.repeat_basic import repeat_cmd

    async with app.test_matcher(repeat_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/repeat 0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群关闭复读功能", None)
        ctx.should_finished(repeat_cmd)
