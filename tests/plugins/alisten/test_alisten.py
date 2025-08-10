from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


def mocked_pick_music_success(name: str, source: str, user_name: str):
    """模拟成功的点歌响应"""
    from src.plugins.alisten.alisten_api import PickMusicResult

    return PickMusicResult(
        success=True,
        message="点歌成功",
        name="测试歌曲",
        source="wy",
        id="123456",
    )


def mocked_pick_music_failure(name: str, source: str, user_name: str):
    """模拟失败的点歌响应"""
    from src.plugins.alisten.alisten_api import PickMusicResult

    return PickMusicResult(
        success=False,
        message="找不到匹配的歌曲",
    )


async def test_music_success(app: App, mocker: MockerFixture):
    """测试音乐点歌成功"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.alisten import music_cmd

    # Mock API call
    mock_api = mocker.patch("src.plugins.alisten.api.pick_music", side_effect=mocked_pick_music_success)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/music test"))
        ctx.receive_event(bot, event)

        ctx.should_call_send(
            event=fake_group_message_event_v11(message=Message("/music test")),
            message="点歌成功！歌曲已加入播放列表\n歌曲：测试歌曲\n来源：网易云音乐",
            at_sender=True,
        )
        ctx.should_finished(music_cmd)

    # 验证 API 调用
    mock_api.assert_called_once_with(name="test", source="wy", user_name="nickname")


async def test_music_failure(app: App, mocker: MockerFixture):
    """测试音乐点歌失败"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.alisten import music_cmd

    # Mock API call
    mock_api = mocker.patch("src.plugins.alisten.api.pick_music", side_effect=mocked_pick_music_failure)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/music test"))
        ctx.receive_event(bot, event)

        ctx.should_call_send(
            event=fake_group_message_event_v11(message=Message("/music test")),
            message="点歌失败：找不到匹配的歌曲",
            at_sender=True,
        )
        ctx.should_finished(music_cmd)

    # 验证 API 调用
    mock_api.assert_called_once_with(name="test", source="wy", user_name="nickname")


async def test_music_bilibili(app: App, mocker: MockerFixture):
    """测试 Bilibili BV 号点歌"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.alisten import music_cmd

    def mocked_pick_music_bilibili(name: str, source: str, user_name: str):
        from src.plugins.alisten.alisten_api import PickMusicResult

        return PickMusicResult(
            success=True,
            message="点歌成功",
            name="【测试】Bilibili视频",
            source="db",
            id="BV1Xx411c7md",
        )

    # Mock API call
    mock_api = mocker.patch("src.plugins.alisten.api.pick_music", side_effect=mocked_pick_music_bilibili)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/music BV1Xx411c7md"))
        ctx.receive_event(bot, event)

        ctx.should_call_send(
            event=fake_group_message_event_v11(message=Message("/music BV1Xx411c7md")),
            message="点歌成功！歌曲已加入播放列表\n歌曲：【测试】Bilibili视频\n来源：Bilibili",
            at_sender=True,
        )
        ctx.should_finished(music_cmd)

    # 验证 API 调用
    mock_api.assert_called_once()


async def test_music_get_arg(app: App, mocker: MockerFixture):
    """测试交互式点歌"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from src.plugins.alisten import music_cmd

    # Mock API call
    mock_api = mocker.patch("src.plugins.alisten.api.pick_music", side_effect=mocked_pick_music_success)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        # 不提供歌曲名，应该询问
        event = fake_group_message_event_v11(message=Message("/music"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你想听哪首歌呢？")
        ctx.should_rejected(music_cmd)

        # 提供无效输入（图片），应该重新询问
        event = fake_group_message_event_v11(message=Message(MessageSegment.image("12")))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你想听哪首歌呢？")
        ctx.should_rejected(music_cmd)

        # 提供有效歌曲名
        event = fake_group_message_event_v11(message=Message("test"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "点歌成功！歌曲已加入播放列表\n歌曲：测试歌曲\n来源：网易云音乐", at_sender=True)
        ctx.should_finished(music_cmd)

    # 验证 API 调用
    mock_api.assert_called_once_with(name="test", source="wy", user_name="nickname")
