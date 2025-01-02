from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


async def test_openai_thread(app: App, mocker: MockerFixture):
    """测试设置并查看会话 ID"""
    from src.plugins.openai import plugin_config, thread_cmd

    mocker.patch.object(plugin_config, "openai_enabled_groups", ["qq_10000"])
    mocker.patch.object(plugin_config, "openai_api_key", "test_key")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/会话 12345678"))
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(thread_cmd)
        ctx.should_pass_permission(thread_cmd)
        ctx.should_call_send(event, "会话 12345678 已设置")
        ctx.should_finished(thread_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/会话 show"))
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(thread_cmd)
        ctx.should_pass_permission(thread_cmd)
        ctx.should_call_send(event, "当前会话 ID 为 12345678")
        ctx.should_finished(thread_cmd)


async def test_openai_set_thread_got(app: App, mocker: MockerFixture):
    """测试设置会话，输入会话 ID"""
    from src.plugins.openai import plugin_config, thread_cmd

    mocker.patch.object(plugin_config, "openai_enabled_groups", ["qq_10000"])
    mocker.patch.object(plugin_config, "openai_api_key", "test_key")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/会话"))
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(thread_cmd)
        ctx.should_pass_permission(thread_cmd)
        ctx.should_call_send(event, "请输入会话 ID（new 表示新建会话）")
        ctx.should_rejected(thread_cmd)

        event = fake_group_message_event_v11(message=Message("12345678"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "会话 12345678 已设置")
        ctx.should_finished(thread_cmd)
