import httpx
import pytest
import respx
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


@pytest.fixture
async def _configs(app: App, mocker: MockerFixture):
    from nonebot_plugin_orm import get_session

    from src.plugins.alisten.models import AlistenConfig

    async with get_session() as session:
        session.add(
            AlistenConfig(
                session_id="QQClient_10000",
                server_url="http://localhost:8080",
                house_id="room123",
                house_password="password123",
            )
        )
        await session.commit()


@pytest.mark.usefixtures("_configs")
@respx.mock(assert_all_called=True)
async def test_music_success(app: App, respx_mock: respx.MockRouter):
    """测试音乐点歌成功"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.alisten import music_cmd

    respx_mock.post("http://localhost:8080/music/pick").mock(
        return_value=httpx.Response(
            status_code=200,
            json={
                "success": True,
                "message": "点歌成功",
                "name": "测试歌曲",
                "source": "网易云音乐",
                "id": "123456",
            },
        )
    )

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


@pytest.mark.usefixtures("_configs")
@respx.mock(assert_all_called=True)
async def test_music_failure(app: App, respx_mock: respx.MockRouter):
    """测试音乐点歌失败"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.alisten import music_cmd

    respx_mock.post("http://localhost:8080/music/pick").mock(
        return_value=httpx.Response(
            status_code=200,
            json={
                "success": False,
                "message": "点歌失败，无法获取音乐信息",
            },
        )
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/music test"))
        ctx.receive_event(bot, event)

        ctx.should_call_send(
            event=fake_group_message_event_v11(message=Message("/music test")),
            message="点歌失败，无法获取音乐信息",
            at_sender=True,
        )
        ctx.should_finished(music_cmd)


@pytest.mark.usefixtures("_configs")
@respx.mock(assert_all_called=True)
async def test_music_bilibili(app: App, respx_mock: respx.MockRouter):
    """测试 Bilibili BV 号点歌"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.alisten import music_cmd

    respx_mock.post("http://localhost:8080/music/pick").mock(
        return_value=httpx.Response(
            status_code=200,
            json={
                "success": True,
                "message": "点歌成功",
                "name": "【测试】Bilibili视频",
                "source": "db",
                "id": "BV1Xx411c7md",
            },
        )
    )

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


@pytest.mark.usefixtures("_configs")
@respx.mock(assert_all_called=True)
async def test_music_get_arg(app: App, respx_mock: respx.MockRouter):
    """测试交互式点歌"""
    from nonebot.adapters.onebot.v11 import Message, MessageSegment

    from src.plugins.alisten import music_cmd

    respx_mock.post("http://localhost:8080/music/pick").mock(
        return_value=httpx.Response(
            status_code=200,
            json={
                "success": True,
                "message": "点歌成功",
                "name": "测试歌曲",
                "source": "网易云音乐",
                "id": "123456",
            },
        )
    )

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
