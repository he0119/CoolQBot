import json
from pathlib import Path

from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


def mocked_get(url: str):
    class MockResponse:
        def __init__(self, json: dict):
            self._json = json

        def json(self):
            return self._json

    test_dir = Path(__file__).parent
    if url == "https://cafemaker.wakingsands.com/search?string=萨维奈舞裙":
        with open(test_dir / "price_search.json", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)
    if url == "https://cafemaker.wakingsands.com/search?string=未命名":
        with open(test_dir / "price_search_not_found.json", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)
    if url == "https://universalis.app/api/v2/猫小胖/10393?listings=6":
        with open(test_dir / "price_10393.json", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)
    if url == "https://universalis.app/api/v2/静语/10393?listings=6":
        with open(test_dir / "price_10393_not_found.json", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)

    return MockResponse({})


async def test_price(app: App, mocker: MockerFixture):
    """测试查价"""
    from src.plugins.ff14.plugins.ff14_price import price_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/查价 萨维奈舞裙 猫小胖"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "萨维奈舞裙 在市场的价格是:\n233100*1  服务器: 静语庄园\n233193*1 HQ 服务器: 静语庄园\n233330*1  服务器: 静语庄园\n233334*1  服务器: 静语庄园\n239166*1 HQ 服务器: 紫水栈桥\n239166*1 HQ 服务器: 紫水栈桥\n数据更新时间: 2021年12月29日 13时00分",
            True,
        )
        ctx.should_finished(price_cmd)

    get.assert_has_calls(
        [
            mocker.call("https://cafemaker.wakingsands.com/search?string=萨维奈舞裙"),
            mocker.call("https://universalis.app/api/v2/猫小胖/10393?listings=6"),
        ]  # type: ignore
    )


async def test_price_default(app: App, mocker: MockerFixture):
    """测试查价，默认值"""
    from src.plugins.ff14.plugins.ff14_price import price_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/查价 默认值"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前设置的默认值为：猫小胖", True)
        ctx.should_finished(price_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/查价 萨维奈舞裙"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "萨维奈舞裙 在市场的价格是:\n233100*1  服务器: 静语庄园\n233193*1 HQ 服务器: 静语庄园\n233330*1  服务器: 静语庄园\n233334*1  服务器: 静语庄园\n239166*1 HQ 服务器: 紫水栈桥\n239166*1 HQ 服务器: 紫水栈桥\n数据更新时间: 2021年12月29日 13时00分",
            True,
        )
        ctx.should_finished(price_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/查价 默认值 静语庄园"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "查询区域默认值设置成功！", True)
        ctx.should_finished(price_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/查价 默认值"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前设置的默认值为：静语庄园", True)
        ctx.should_finished(price_cmd)

    get.assert_has_calls(
        [
            mocker.call("https://cafemaker.wakingsands.com/search?string=萨维奈舞裙"),
            mocker.call("https://universalis.app/api/v2/猫小胖/10393?listings=6"),
        ]  # type: ignore
    )


async def test_price_item_not_found(app: App, mocker: MockerFixture):
    """测试查价，物品不存在"""
    from src.plugins.ff14.plugins.ff14_price import price_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/查价 未命名 猫小胖"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "抱歉，没有找到 未命名，请检查物品名称是否正确。",
            True,
        )
        ctx.should_finished(price_cmd)

    get.assert_called_once_with("https://cafemaker.wakingsands.com/search?string=未命名")


async def test_price_world_not_found(app: App, mocker: MockerFixture):
    """测试查价，服务器/大区不存在"""
    from src.plugins.ff14.plugins.ff14_price import price_cmd

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/查价 萨维奈舞裙 静语"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "抱歉，没有找到 静语 的数据，请检查大区或服务器名称是否正确。",
            True,
        )
        ctx.should_finished(price_cmd)

    get.assert_has_calls(
        [
            mocker.call("https://cafemaker.wakingsands.com/search?string=萨维奈舞裙"),
            mocker.call("https://universalis.app/api/v2/静语/10393?listings=6"),
        ]  # type: ignore
    )


async def test_price_help(app: App):
    """测试查价，参数不足两个的情况"""
    from src.plugins.ff14.plugins.ff14_price import price_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/查价"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "最终幻想XIV 价格查询\n\n查询大区中的最低价格\n/查价 萨维奈舞裙 猫小胖\n查询服务器中的最低价格\n/查价 萨维奈舞裙 静语庄园\n设置默认查询的区域\n/查价 默认值 静语庄园\n查询当前设置的默认值\n/查价 默认值",
            True,
        )
        ctx.should_finished(price_cmd)
