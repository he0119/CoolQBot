import pytest
from nonebug import App

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.help",)], indirect=True)
async def test_sort_commands(app: App):
    from src.plugins.help.commands import sort_commands

    cmds = [
        ("ff14", "nuannuan"),
        ("时尚品鉴",),
        ("最终幻想14", "时尚品鉴"),
        ("nuannuan",),
    ]
    assert sort_commands(cmds) == [
        ("ff14", "nuannuan"),
        ("nuannuan",),
        ("最终幻想14", "时尚品鉴"),
        ("时尚品鉴",),
    ]

    cmds = [
        ("时尚品鉴",),
        ("最终幻想14", "时尚品鉴"),
        ("nuannuan",),
    ]
    assert sort_commands(cmds) == [
        ("nuannuan",),
        ("最终幻想14", "时尚品鉴"),
        ("时尚品鉴",),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.help",)], indirect=True)
async def test_help(app: App):
    """测试帮助"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.help import help_cmd

    async with app.test_matcher(help_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/help"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "获取帮助\n\n获取所有支持的命令\n/help list\n获取某个命令的帮助\n/help 命令名",
            True,
        )
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.help",)], indirect=True)
async def test_help_list(app: App):
    """测试帮助，查看所有命令"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.help import help_cmd

    async with app.test_matcher(help_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/help list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "命令（别名）列表：\nhelp(帮助)", True)
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.help",)], indirect=True)
async def test_help_help(app: App):
    """测试帮助，获取帮助插件帮助"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.help import help_cmd

    async with app.test_matcher(help_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/help help"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "获取帮助\n\n获取所有支持的命令\n/help list\n获取某个命令的帮助\n/help 命令名",
            True,
        )
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.help",)], indirect=True)
async def test_help_not_found(app: App):
    """测试帮助，插件不存在"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.help import help_cmd

    async with app.test_matcher(help_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/help test"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入支持的命令", True)
        ctx.should_finished()
