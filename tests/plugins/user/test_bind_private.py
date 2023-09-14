from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_private_message_event_v11


async def test_bind_private(app: App, patch_current_time, mocker: MockerFixture):
    """私聊绑定用户"""
    from src.plugins.user import bind_cmd, user_cmd

    mocked_random = mocker.patch("src.plugins.user.random.randint")
    mocked_random.return_value = 123456

    with patch_current_time("2023-09-14 10:46:10.416389", tick=False):
        async with app.test_matcher(user_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/user"), user_id=1)

            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_stranger_info",
                {"user_id": 1},
                {
                    "user_id": 1,
                    "nickname": "nickname1",
                },
            )
            ctx.should_call_send(
                event,
                "用户 ID：1\n用户名：nickname1\n用户创建日期：2023-09-14 10:46:10.416389+08:00\n用户所在平台 ID：1\n用户所在平台：qq",
                True,
            )
            ctx.should_finished(user_cmd)

        async with app.test_matcher(user_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/user"))

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
                "用户 ID：2\n用户名：nickname10\n用户创建日期：2023-09-14 10:46:10.416389+08:00\n用户所在平台 ID：10\n用户所在平台：qq",
                True,
            )
            ctx.should_finished(user_cmd)

        async with app.test_matcher(bind_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/bind"))

            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                "命令 bind 可用于在多个平台间绑定用户数据。绑定过程中，原始平台的用户数据将完全保留，而目标平台的用户数据将被原始平台的数据所覆盖。\n请确认当前平台是你的目标平台，并在 5 分钟内使用你的账号在原始平台内向机器人发送以下文本：\n/bind nonebot/123456\n绑定完成后，你可以随时使用「bind -r」来解除绑定状态。",
                True,
            )
            ctx.should_finished(bind_cmd)

        async with app.test_matcher(bind_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(
                message=Message("/bind nonebot/123456"), user_id=1
            )

            ctx.receive_event(bot, event)
            ctx.should_call_send(event, "绑定成功", True)
            ctx.should_finished(bind_cmd)

        async with app.test_matcher(user_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/user"), user_id=1)

            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                "用户 ID：1\n用户名：nickname1\n用户创建日期：2023-09-14 10:46:10.416389+08:00\n用户所在平台 ID：1\n用户所在平台：qq",
                True,
            )
            ctx.should_finished(user_cmd)

        async with app.test_matcher(user_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/user"))

            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                "用户 ID：1\n用户名：nickname1\n用户创建日期：2023-09-14 10:46:10.416389+08:00\n用户所在平台 ID：10\n用户所在平台：qq",
                True,
            )
            ctx.should_finished(user_cmd)


async def test_bind_private_invalid_token(
    app: App, patch_current_time, mocker: MockerFixture
):
    """私聊绑定用户，无效的令牌"""
    from src.plugins.user import bind_cmd, user_cmd

    mocked_random = mocker.patch("src.plugins.user.random.randint")
    mocked_random.return_value = 123456

    with patch_current_time("2023-09-14 10:46:10.416389", tick=False):
        async with app.test_matcher(user_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/user"), user_id=1)

            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_stranger_info",
                {"user_id": 1},
                {
                    "user_id": 1,
                    "nickname": "nickname1",
                },
            )
            ctx.should_call_send(
                event,
                "用户 ID：1\n用户名：nickname1\n用户创建日期：2023-09-14 10:46:10.416389+08:00\n用户所在平台 ID：1\n用户所在平台：qq",
                True,
            )
            ctx.should_finished(user_cmd)

        async with app.test_matcher(user_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/user"))

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
                "用户 ID：2\n用户名：nickname10\n用户创建日期：2023-09-14 10:46:10.416389+08:00\n用户所在平台 ID：10\n用户所在平台：qq",
                True,
            )
            ctx.should_finished(user_cmd)

        async with app.test_matcher(bind_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/bind"))

            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                "命令 bind 可用于在多个平台间绑定用户数据。绑定过程中，原始平台的用户数据将完全保留，而目标平台的用户数据将被原始平台的数据所覆盖。\n请确认当前平台是你的目标平台，并在 5 分钟内使用你的账号在原始平台内向机器人发送以下文本：\n/bind nonebot/123456\n绑定完成后，你可以随时使用「bind -r」来解除绑定状态。",
                True,
            )
            ctx.should_finished(bind_cmd)

        async with app.test_matcher(bind_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(
                message=Message("/bind nonebot/1"), user_id=1
            )

            ctx.receive_event(bot, event)
            ctx.should_call_send(event, "令牌不存在或已过期", True)
            ctx.should_finished(bind_cmd)

        async with app.test_matcher(user_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/user"), user_id=1)

            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                "用户 ID：1\n用户名：nickname1\n用户创建日期：2023-09-14 10:46:10.416389+08:00\n用户所在平台 ID：1\n用户所在平台：qq",
                True,
            )
            ctx.should_finished(user_cmd)

        async with app.test_matcher(user_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_private_message_event_v11(message=Message("/user"))

            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                "用户 ID：2\n用户名：nickname10\n用户创建日期：2023-09-14 10:46:10.416389+08:00\n用户所在平台 ID：10\n用户所在平台：qq",
                True,
            )
            ctx.should_finished(user_cmd)
