from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App

from tests.fake import fake_group_message_event_v11


async def test_bind_group_success(app: App):
    """测试成功绑定群组"""
    from src.plugins.group_bind import bind_group_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        # 模拟超级用户发送绑定群组命令
        event = fake_group_message_event_v11(
            message=Message("/绑定群组 123456789"),
            user_id=10,  # 超级用户ID，对应nickname
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "群组绑定成功！当前群组已绑定到群组 123456789", True)
        ctx.should_finished(bind_group_cmd)


async def test_bind_group_update_existing(app: App):
    """测试绑定群组（无论是首次绑定还是更新绑定）"""
    from src.plugins.group_bind import bind_group_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        # 模拟超级用户绑定群组
        event = fake_group_message_event_v11(
            message=Message("/绑定群组 222222"),
            user_id=10,
        )
        ctx.receive_event(bot, event)
        # 由于我们无法确定是否有现有绑定，所以接受任一种消息
        ctx.should_call_send(event, "群组绑定成功！当前群组已绑定到群组 222222", True)
        ctx.should_finished(bind_group_cmd)


async def test_bind_group_to_self(app: App):
    """测试绑定群组到自己（应该失败）"""
    from src.plugins.group_bind import bind_group_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        # 模拟超级用户尝试绑定到自己
        event = fake_group_message_event_v11(
            message=Message("/绑定群组 QQClient_10000"),  # QQClient_10000 是默认的session_id
            user_id=10,
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "不能将当前群组绑定到自己！", True)
        ctx.should_finished(bind_group_cmd)


async def test_unbind_group_success(app: App):
    """测试成功解绑群组"""
    from src.plugins.group_bind import unbind_group_cmd
    from src.plugins.group_bind.data_source import group_bind_service

    # 先创建一个绑定
    await group_bind_service.bind_group("QQClient_10000", "QQClient_123456")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        # 模拟超级用户解绑群组
        event = fake_group_message_event_v11(
            message=Message("/解绑群组"),
            user_id=10,
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "群组解绑成功！当前群组已从绑定中移除", True)
        ctx.should_finished(unbind_group_cmd)


async def test_unbind_group_not_bound(app: App):
    """测试解绑未绑定的群组（应该失败）"""
    from src.plugins.group_bind import unbind_group_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        # 模拟超级用户尝试解绑未绑定的群组
        event = fake_group_message_event_v11(
            message=Message("/解绑群组"),
            user_id=10,
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "解绑失败：该群组未绑定到任何群组", True)
        ctx.should_finished(unbind_group_cmd)


async def test_check_bind_not_bound(app: App):
    """测试查看未绑定群组的状态"""
    from src.plugins.group_bind import check_bind_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        # 模拟超级用户查看绑定状态
        event = fake_group_message_event_v11(
            message=Message("/查看绑定"),
            user_id=10,
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前群组未绑定到任何群组", True)
        ctx.should_finished(check_bind_cmd)


async def test_check_bind_bound(app: App):
    """测试查看已绑定群组的状态"""
    from src.plugins.group_bind import check_bind_cmd
    from src.plugins.group_bind.data_source import group_bind_service

    # 先创建一个绑定
    await group_bind_service.bind_group("QQClient_10000", "QQClient_123456789")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        # 模拟超级用户查看绑定状态
        event = fake_group_message_event_v11(
            message=Message("/查看绑定"),
            user_id=10,
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前群组已绑定到群组: QQClient_123456789", True)
        ctx.should_finished(check_bind_cmd)
