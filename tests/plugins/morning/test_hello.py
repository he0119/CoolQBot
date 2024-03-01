from nonebot.adapters.onebot.v11 import Bot, Message
from nonebug import App
from sqlalchemy import select

from tests.fake import fake_group_message_event_v11


async def test_hello_enabled(app: App):
    """测试启动问候已开启的情况"""
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_saa import TargetQQGroup

    from src.plugins.morning.plugins.hello import Hello, hello_cmd

    async with get_session() as session:
        session.add(
            Hello(target=TargetQQGroup(group_id=10000).model_dump(), bot_id="test")
        )
        await session.commit()

    async with app.test_matcher(hello_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/hello"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "启动问候功能开启中", None)
        ctx.should_finished()


async def test_hello_not_enabled(app: App):
    """测试启动问候关闭的情况"""

    from src.plugins.morning.plugins.hello import hello_cmd

    async with app.test_matcher(hello_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/hello"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "启动问候功能关闭中", None)
        ctx.should_finished()


async def test_hello_enable(app: App):
    """测试启动问候，在群里启用的情况"""
    from nonebot_plugin_orm import get_session
    from nonebot_plugin_saa import TargetQQGroup

    from src.plugins.morning.plugins.hello import Hello, hello_cmd

    async with get_session() as session:
        groups = (await session.scalars(select(Hello))).all()
        assert len(groups) == 0

    async with app.test_matcher(hello_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/hello 1"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群开启启动问候功能", None)
        ctx.should_finished()

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
        session.add(
            Hello(target=TargetQQGroup(group_id=10000).model_dump(), bot_id="test")
        )
        await session.commit()

    async with app.test_matcher(hello_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/hello 0"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已在本群关闭启动问候功能", None)
        ctx.should_finished()

    async with get_session() as session:
        groups = (await session.scalars(select(Hello))).all()
        assert len(groups) == 0
