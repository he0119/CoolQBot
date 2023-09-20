from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App

from tests.fake import fake_group_message_event_v11, fake_private_message_event_v11


async def test_user(app: App, patch_current_time):
    """获取用户信息"""
    from src.user import user_cmd

    with patch_current_time("2023-09-14 10:46:10.416389", tick=False):
        async with app.test_matcher(user_cmd) as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_group_message_event_v11(message=Message("/user"))

            ctx.receive_event(bot, event)
            ctx.should_call_api(
                "get_group_member_info",
                {"group_id": 10000, "user_id": 10},
                {
                    "user_id": 10,
                    "nickname": "nickname",
                    "card": "card",
                },
            )
            ctx.should_call_send(
                event,
                "用户 ID：1\n用户名：nickname\n用户创建日期：2023-09-14 10:46:10.416389+08:00\n用户所在平台 ID：10\n用户所在平台：qq",
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
                "用户 ID：1\n用户名：nickname\n用户创建日期：2023-09-14 10:46:10.416389+08:00\n用户所在平台 ID：10\n用户所在平台：qq",
                True,
            )
            ctx.should_finished(user_cmd)
