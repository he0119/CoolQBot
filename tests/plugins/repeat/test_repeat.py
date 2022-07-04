from datetime import datetime

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
async def test_repeat(app: App, mocker: MockerFixture):
    """测试复读"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.repeat")
    from src.plugins.repeat import plugin_config, recorder_obj
    from src.plugins.repeat.plugins.basic import repeat_message

    mocked_rule_datetime = mocker.patch(
        "src.plugins.repeat.plugins.basic.repeat_rule.datetime"
    )
    mocked_rule_datetime.now.return_value = datetime(2021, 1, 1, 0, 0, 0)
    mocked_recorder_datetime = mocker.patch("src.plugins.repeat.recorder.datetime")
    mocked_recorder_datetime.now.side_effect = [
        datetime(2020, 1, 1, 0, 0, 0),  # add_new_group
        datetime(2021, 1, 1, 1, 0, 0),  # add_msg_number_list
        datetime(2021, 1, 1, 2, 0, 0),  # reset_last_message_on
        datetime(2021, 1, 1, 3, 0, 0),  # add_repeat_list
    ]
    mocked_random = mocker.patch(
        "src.plugins.repeat.plugins.basic.repeat_rule.secrets.SystemRandom"
    )
    mocked_random().randint.return_value = 1

    plugin_config.group_id = [10000]
    recorder_obj.add_new_group()

    mocked_recorder_datetime.now.assert_called_once()

    async with app.test_matcher(repeat_message) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("123"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, event.message, "result")
        ctx.should_finished()

    assert mocked_recorder_datetime.now.call_count == 4
    assert recorder_obj.last_message_on(10000) == datetime(2021, 1, 1, 2, 0, 0)
    assert recorder_obj.repeat_list(10000) == {10: 1}


@pytest.mark.asyncio
async def test_repeat_enabled(app: App):
    """测试复读已开启的情况"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.repeat")
    from src.plugins.repeat import plugin_config
    from src.plugins.repeat.plugins.basic import repeat_cmd

    plugin_config.group_id = [10000]

    async with app.test_matcher(repeat_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/repeat"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "复读功能开启中", "result")
        ctx.should_finished()


@pytest.mark.asyncio
async def test_repeat_not_enabled(app: App):
    """测试复读关闭的情况"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.repeat")
    from src.plugins.repeat import plugin_config
    from src.plugins.repeat.plugins.basic import repeat_cmd

    async with app.test_matcher(repeat_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/repeat"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "复读功能关闭中", "result")
        ctx.should_finished()


@pytest.mark.asyncio
async def test_repeat_enable(app: App):
    """测试复读，在群里启用的情况"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.repeat")
    from src.plugins.repeat import plugin_config
    from src.plugins.repeat.plugins.basic import repeat_cmd

    assert plugin_config.group_id == []

    async with app.test_matcher(repeat_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/repeat 1"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群开启复读功能", "result")
        ctx.should_finished()

    assert plugin_config.group_id == [10000]


@pytest.mark.asyncio
async def test_repeat_disable(app: App):
    """测试复读，在群里关闭的情况"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.repeat")
    from src.plugins.repeat import plugin_config
    from src.plugins.repeat.plugins.basic import repeat_cmd

    plugin_config.group_id = [10000]

    assert plugin_config.group_id == [10000]

    async with app.test_matcher(repeat_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/repeat 0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群关闭复读功能", "result")
        ctx.should_finished()

    assert plugin_config.group_id == []
