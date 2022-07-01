import pytest
from nonebug import App

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
async def test_sort_commands(app: App):
    from src.plugins.help.data_source import sort_commands

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
async def test_help(app: App):
    """测试帮助"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.help")
    from src.plugins.help import help_cmd

    async with app.test_matcher(help_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/help"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "帮助\n\n获取插件列表\n/help list\n获取某个插件的帮助\n/help 插件名",
            True,
        )
        ctx.should_finished()


@pytest.mark.asyncio
async def test_help_list(app: App):
    """测试帮助，查看所有插件"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.help")

    from src.plugins.help import help_cmd

    async with app.test_matcher(help_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/help list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "插件列表：\n帮助 # 获取插件帮助信息", True)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_help_help(app: App):
    """测试帮助，获取帮助插件帮助"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.help")
    from src.plugins.help import help_cmd

    async with app.test_matcher(help_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/help 帮助"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "帮助\n\n获取插件列表\n/help list\n获取某个插件的帮助\n/help 插件名",
            True,
        )
        ctx.should_finished()


@pytest.mark.asyncio
async def test_help_not_found(app: App):
    """测试帮助，插件不存在"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.help")

    from src.plugins.help import help_cmd

    async with app.test_matcher(help_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/help test"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "请输入支持的插件名", True)
        ctx.should_finished()
