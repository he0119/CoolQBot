import json
from pathlib import Path

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


def mocked_get(url: str, **kwargs):
    class MockResponse:
        def __init__(self, json: dict):
            self._json = json

        def json(self):
            return self._json

    test_dir = Path(__file__).parent
    if (
        url
        == "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?game_biz=hk4e_cn"
    ):
        with open(test_dir / "game_roles.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)
    if (
        url
        == "https://api-takumi-record.mihoyo.com/game_record/app/genshin/api/dailyNote"
    ):
        if kwargs["headers"]["Cookie"] == "full":
            with open(test_dir / "daily_note_full.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with open(test_dir / "daily_note.json", "r", encoding="utf-8") as f:
                data = json.load(f)

        return MockResponse(data)

    return MockResponse({})


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.genshin",)], indirect=True)
async def test_daily_note(
    app: App,
    mocker: MockerFixture,
):
    """测试原神实时便笺"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.genshin import daily_note_cmd
    from src.plugins.genshin.config import set_cookie

    set_cookie(10, "test")

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(daily_note_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/ys.dailynote"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "原粹树脂: 93/160 (8小时54分钟25秒后全部恢复)\n洞天宝钱: 960/2400 (后天22分钟41秒后达到存储上限)\n每日委托任务: 0/4 (今日完成委托次数不足)\n值得铭记的强敌: 0/3 (本周剩余消耗减半次数)\n探索派遣: 5/5\n角色1: 4小时2分钟33秒后完成派遣\n角色2: 4小时2分钟33秒后完成派遣\n角色3: 4小时2分钟33秒后完成派遣\n角色4: 4小时2分钟33秒后完成派遣\n角色5: 4小时2分钟33秒后完成派遣",
            "",
        )
        ctx.should_finished()

    assert get.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.genshin",)], indirect=True)
async def test_daily_note_full(
    app: App,
    mocker: MockerFixture,
):
    """测试原神实时便笺，体力满的情况"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.genshin import daily_note_cmd
    from src.plugins.genshin.config import set_cookie

    set_cookie(10, "full")

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(daily_note_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/ys.dailynote"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "原粹树脂: 160/160 (已完全恢复)\n洞天宝钱: 2400/2400 (已满)\n每日委托任务: 0/4 (今日完成委托次数不足)\n值得铭记的强敌: 0/3 (本周剩余消耗减半次数)\n探索派遣: 5/5\n角色1: 已完成派遣\n角色2: 已完成派遣\n角色3: 已完成派遣\n角色4: 已完成派遣\n角色5: 已完成派遣",
            "",
        )
        ctx.should_finished()

    assert get.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.genshin",)], indirect=True)
async def test_daily_note_not_bind(app: App):
    """测试原神实时便笺，未绑定账号"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.genshin import daily_note_cmd

    async with app.test_matcher(daily_note_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/ys.dailynote"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你还没有绑定账号，请私聊机器人绑定账号绑定后查询", "")
        ctx.should_finished()
