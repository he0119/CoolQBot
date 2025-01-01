from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


async def test_openai_message(app: App, mocker: MockerFixture):
    """测试响应数据"""
    from src.plugins.openai import openai_message, plugin_config

    mocker.patch.object(plugin_config, "openai_enabled_groups", ["qq_10000"])
    mocker.patch.object(plugin_config, "openai_api_key", "test_key")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("你好呀"), to_me=True)
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(openai_message)
        ctx.should_call_send(event, "请先创建/指定会话")
        ctx.should_finished(openai_message)


async def test_openai_message_not_enabled(app: App, mocker: MockerFixture):
    """没有启用的群组"""
    from src.plugins.openai import openai_message, plugin_config

    mocker.patch.object(plugin_config, "openai_api_key", "test_key")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("你好呀"), to_me=True)
        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(openai_message)


async def test_openai_message_missing_key(app: App, mocker: MockerFixture):
    """没有 API Key"""
    from src.plugins.openai import openai_message, plugin_config

    mocker.patch.object(plugin_config, "openai_enabled_groups", ["qq_10000"])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("你好呀"), to_me=True)
        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(openai_message)
