import pytest
from nonebug import App

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.morning",)], indirect=True)
async def test_hello_enabled(app: App):
    """测试启动问候已开启的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.morning import hello_cmd, plugin_config

    plugin_config.hello_group_id = [10000]

    async with app.test_matcher(hello_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/hello"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "启动问候功能开启中", "result")
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.morning",)], indirect=True)
async def test_hello_not_enabled(app: App):
    """测试启动问候关闭的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.morning import hello_cmd

    async with app.test_matcher(hello_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/hello"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "启动问候功能关闭中", "result")
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.morning",)], indirect=True)
async def test_hello_enable(app: App):
    """测试启动问候，在群里启用的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.morning import hello_cmd, plugin_config

    assert plugin_config.hello_group_id == []

    async with app.test_matcher(hello_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/hello 1"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群开启启动问候功能", "result")
        ctx.should_finished()

    assert plugin_config.hello_group_id == [10000]


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.morning",)], indirect=True)
async def test_hello_disable(app: App):
    """测试启动问候，在群里关闭的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.morning import hello_cmd, plugin_config

    plugin_config.hello_group_id = [10000]

    assert plugin_config.hello_group_id == [10000]

    async with app.test_matcher(hello_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/hello 0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群关闭启动问候功能", "result")
        ctx.should_finished()

    assert plugin_config.hello_group_id == []