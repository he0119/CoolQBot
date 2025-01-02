from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


async def test_openai_assistant(app: App, mocker: MockerFixture):
    """测试设置并查看助手 ID"""
    from src.plugins.openai import assistant_cmd, plugin_config

    mocker.patch.object(plugin_config, "openai_enabled_groups", ["qq_10000"])
    mocker.patch.object(plugin_config, "openai_api_key", "test_key")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/助手 12345678"))
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(assistant_cmd)
        ctx.should_pass_permission(assistant_cmd)
        ctx.should_call_send(event, "助手 12345678 已设置")
        ctx.should_finished(assistant_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/助手 show"))
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(assistant_cmd)
        ctx.should_pass_permission(assistant_cmd)
        ctx.should_call_send(event, "当前助手 ID 为 12345678")
        ctx.should_finished(assistant_cmd)


async def test_openai_set_assistant_got(app: App, mocker: MockerFixture):
    """测试设置助手，输入助手 ID"""
    from src.plugins.openai import assistant_cmd, plugin_config

    mocker.patch.object(plugin_config, "openai_enabled_groups", ["qq_10000"])
    mocker.patch.object(plugin_config, "openai_api_key", "test_key")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/助手"))
        ctx.receive_event(bot, event)
        ctx.should_pass_rule(assistant_cmd)
        ctx.should_pass_permission(assistant_cmd)
        ctx.should_call_send(event, "请输入助手 ID（new 表示新建助手）")
        ctx.should_rejected(assistant_cmd)

        event = fake_group_message_event_v11(message=Message("12345678"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "助手 12345678 已设置")
        ctx.should_finished(assistant_cmd)
