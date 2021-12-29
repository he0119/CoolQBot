import json
from pathlib import Path
from typing import TYPE_CHECKING, Type

import pytest
from nonebug import App
from pytest_mock import MockerFixture

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import GroupMessageEvent


def mocked_get(url: str):
    class MockResponse:
        def __init__(self, json: dict):
            self._json = json

        def json(self):
            return self._json

    test_dir = Path(__file__).parent
    if url == "https://cafemaker.wakingsands.com/search?string=萨维奈舞裙":
        with open(test_dir / "price_search.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)
    if url == "https://cafemaker.wakingsands.com/search?string=未命名":
        with open(test_dir / "price_search_not_found.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)
    if url == "https://universalis.app/api/v2/猫小胖/10393?listings=6":
        with open(test_dir / "price_10393.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)
    if url == "https://universalis.app/api/v2/静语/10393?listings=6":
        with open(test_dir / "price_10393_not_found.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)

    return MockResponse({})


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.ff14",)], indirect=True)
async def test_price(
    app: App,
    mocker: MockerFixture,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试查价"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ff14 import price_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(price_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/查价 萨维奈舞裙 猫小胖"))
        state = {
            "_prefix": {
                "command": ("查价",),
                "command_arg": Message("萨维奈舞裙 猫小胖"),
            }
        }

        ctx.receive_event(bot, event, state)
        ctx.should_call_send(
            event,
            "萨维奈舞裙 在市场的价格是:\n233100*1  服务器: 静语庄园\n233193*1 HQ 服务器: 静语庄园\n233330*1  服务器: 静语庄园\n233334*1  服务器: 静语庄园\n239166*1 HQ 服务器: 紫水栈桥\n239166*1 HQ 服务器: 紫水栈桥\n数据更新时间: 2021年12月29日 05时00分",
            "result",
        )
        ctx.should_finished()

    get.assert_has_calls(
        [
            mocker.call("https://cafemaker.wakingsands.com/search?string=萨维奈舞裙"),
            mocker.call("https://universalis.app/api/v2/猫小胖/10393?listings=6"),
        ]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.ff14",)], indirect=True)
async def test_price_item_not_found(
    app: App,
    mocker: MockerFixture,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试查价，物品不存在"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ff14 import price_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(price_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/查价 未命名 猫小胖"))
        state = {
            "_prefix": {
                "command": ("查价",),
                "command_arg": Message("未命名 猫小胖"),
            }
        }

        ctx.receive_event(bot, event, state)
        ctx.should_call_send(
            event,
            "抱歉，没有找到 未命名，请检查物品名称是否正确。",
            "result",
        )
        ctx.should_finished()

    get.assert_called_once_with("https://cafemaker.wakingsands.com/search?string=未命名")


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.ff14",)], indirect=True)
async def test_price_world_not_found(
    app: App,
    mocker: MockerFixture,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试查价，服务器/大区不存在"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ff14 import price_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(price_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/查价 萨维奈舞裙 静语"))
        state = {
            "_prefix": {
                "command": ("查价",),
                "command_arg": Message("萨维奈舞裙 静语"),
            }
        }

        ctx.receive_event(bot, event, state)
        ctx.should_call_send(
            event,
            "抱歉，没有找到 静语 的数据，请检查大区或服务器名称是否正确。",
            "result",
        )
        ctx.should_finished()

    get.assert_has_calls(
        [
            mocker.call("https://cafemaker.wakingsands.com/search?string=萨维奈舞裙"),
            mocker.call("https://universalis.app/api/v2/静语/10393?listings=6"),
        ]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.ff14",)], indirect=True)
async def test_price_help(
    app: App,
    fake_group_message_event: Type["GroupMessageEvent"],
):
    """测试查价，参数不足两个的情况"""
    from nonebot import get_driver
    from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
    from nonebug.mixin.call_api.fake import make_fake_adapter, make_fake_bot

    from src.plugins.ff14 import price_cmd

    async with app.test_matcher(price_cmd) as ctx:
        adapter = make_fake_adapter(Adapter)(get_driver(), ctx)
        bot = make_fake_bot(Bot)(adapter, "1")
        event = fake_group_message_event(message=Message("/查价"))
        state = {
            "_prefix": {
                "command": ("查价",),
                "command_arg": Message(),
            }
        }

        ctx.receive_event(bot, event, state)
        ctx.should_call_send(
            event,
            "最终幻想XIV 价格查询\n\n查询大区中的最低价格\n/查价 萨维奈舞裙 猫小胖\n查询服务器中的最低价格\n/查价 萨维奈舞裙 静语庄园",
            "result",
        )
        ctx.should_finished()
