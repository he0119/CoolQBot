from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from pytest_mock import MockerFixture
from sqlalchemy import select

from tests.fake import fake_private_message_event_v11


async def test_remove_bind(app: App, patch_current_time, mocker: MockerFixture):
    """解除绑定"""
    from nonebot_plugin_datastore import create_session

    from src.user import bind_cmd
    from src.user.models import Bind, User

    with patch_current_time("2023-09-14 10:46:10.416389", tick=False):
        async with create_session() as session:
            user = User(id=1, name="nickname")
            user2 = User(id=2, name="nickname2")
            session.add(user)
            session.add(user2)
            bind = Bind(pid=1, platform="qq", auser=user, buser=user)
            bind2 = Bind(pid=10, platform="qq", auser=user, buser=user2)
            session.add(bind)
            session.add(bind2)
            await session.commit()

        async with app.test_matcher(bind_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/bind -r"))

            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_stranger_info",
                {"user_id": 10},
                {
                    "user_id": 10,
                    "nickname": "nickname10",
                },
            )
            ctx.should_call_send(
                event,
                "解绑成功",
                True,
            )
            ctx.should_finished(bind_cmd)

        async with create_session() as session:
            bind = (await session.scalars(select(Bind).where(Bind.pid == 10))).one()
            assert bind.aid == 2


async def test_remove_bind_self(app: App, patch_current_time, mocker: MockerFixture):
    """解除最初的绑定"""
    from src.user import bind_cmd

    with patch_current_time("2023-09-14 10:46:10.416389", tick=False):
        async with app.test_matcher(bind_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/bind -r"))

            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_stranger_info",
                {"user_id": 10},
                {
                    "user_id": 10,
                    "nickname": "nickname10",
                },
            )
            ctx.should_call_send(
                event,
                "不能解绑最初绑定的账号",
                True,
            )
            ctx.should_finished(bind_cmd)
