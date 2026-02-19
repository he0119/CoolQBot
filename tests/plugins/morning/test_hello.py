from nonebot import get_adapter, get_driver
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from sqlalchemy import select

from tests.fake import fake_group_message_event_v11


async def test_hello_enabled(app: App):
    """测试启动问候已开启的情况"""
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_saa import TargetQQGroup

    from src.plugins.morning.plugins.hello import Hello, hello_cmd

    async with get_session() as session:
        session.add(Hello(target=TargetQQGroup(group_id=10000).model_dump(), bot_id="test"))
        await session.commit()

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/hello"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "启动问候功能开启中", None)
        ctx.should_finished(hello_cmd)


async def test_hello_disabled(app: App):
    """测试启动问候关闭的情况"""

    from src.plugins.morning.plugins.hello import hello_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/hello"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "启动问候功能关闭中", None)
        ctx.should_finished(hello_cmd)


async def test_hello_enable(app: App):
    """测试启动问候，在群里启用的情况"""
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_saa import TargetQQGroup

    from src.plugins.morning.plugins.hello import Hello, hello_cmd

    async with get_session() as session:
        groups = (await session.scalars(select(Hello))).all()
        assert len(groups) == 0

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/hello 1"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群开启启动问候功能", None)
        ctx.should_finished(hello_cmd)

    async with get_session() as session:
        groups = (await session.scalars(select(Hello))).all()
        assert len(groups) == 1
        assert groups[0].saa_target == TargetQQGroup(group_id=10000)


async def test_hello_disable(app: App):
    """测试启动问候，在群里关闭的情况"""
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_saa import TargetQQGroup

    from src.plugins.morning.plugins.hello import Hello, hello_cmd

    async with get_session() as session:
        session.add(Hello(target=TargetQQGroup(group_id=10000).model_dump(), bot_id="test"))
        await session.commit()

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/hello 0"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群关闭启动问候功能", None)
        ctx.should_finished(hello_cmd)

    async with get_session() as session:
        groups = (await session.scalars(select(Hello))).all()
        assert len(groups) == 0


async def test_hello_on_connect(app: App):
    """测试启动时发送问候功能 - 验证数据库连接正常"""
    from unittest.mock import AsyncMock, patch

    from nonebot_plugin_orm import get_session
    from nonebot_plugin_saa import TargetQQGroup

    from src.plugins.morning.plugins.hello import Hello, hello_on_connect

    # 创建一个测试群
    async with get_session() as session:
        session.add(Hello(target=TargetQQGroup(group_id=10000).model_dump(), bot_id="test"))
        await session.commit()

    # 创建一个模拟的 Bot 对象
    adapter = get_adapter(Adapter)
    async with app.test_api() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="test")

        # 模拟消息发送，让它不真正发送
        with patch("nonebot_plugin_saa.Text.send_to", new_callable=AsyncMock) as mock_send:
            # 调用启动问候函数
            await hello_on_connect(bot)

            # 验证至少尝试发送了一次（说明数据库查询成功）
            assert mock_send.call_count >= 1

        # 验证数据库查询正常工作（不会抛出"no active connection"错误）
        async with get_session() as session:
            groups = (await session.scalars(select(Hello).where(Hello.bot_id == "test"))).all()
            assert len(groups) == 1
