import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App
from pytest_mock import MockerFixture
from respx import MockRouter
from sqlalchemy import delete

from tests.fake import fake_group_message_event_v11


@pytest.fixture
async def app(app: App):
    yield app

    # 清理数据库
    from nonebot_plugin_orm import get_session

    from src.plugins.ff14.plugins.ff14_fflogs.data import FFLOGS_DATA
    from src.plugins.ff14.plugins.ff14_fflogs.models import User

    async with get_session() as session, session.begin():
        await session.execute(delete(User))

    # 清除缓存的数据
    FFLOGS_DATA._data = None


@pytest.fixture
async def fflogs_data(app: App) -> dict[str, Any]:
    path = Path(__file__).parent / "fflogs_data.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@pytest.fixture
async def fflogs_character_rankings(app: App) -> dict[str, Any]:
    path = Path(__file__).parent / "fflogs_character_rankings.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@pytest.fixture
async def fflogs_job_rankings(app: App) -> dict[str, Any]:
    path = Path(__file__).parent / "fflogs_job_rankings.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@pytest.fixture
async def fflogs_job_rankings_empty(app: App) -> dict[str, Any]:
    path = Path(__file__).parent / "fflogs_job_rankings_empty.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


async def test_dps_missing_token(app: App):
    """测试 FFLOGS，缺少 Token 的情况"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs_cmd

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps me"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "对不起，Token 未设置，无法查询数据。\n请先使用命令\n/dps token <token>\n配置好 Token 后再尝试查询数据。",
            True,
        )
        ctx.should_finished(fflogs_cmd)


async def test_dps_cache(app: App):
    """测试 FFLOGS，设置缓存的情况"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs_cmd, plugin_data

    await plugin_data.config.set("token", "test")

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前没有缓存副本。", True)
        ctx.should_finished(fflogs_cmd)

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache add p1s"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已添加副本 p1s。", True)
        ctx.should_finished(fflogs_cmd)

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前缓存的副本有：\np1s", True)
        ctx.should_finished(fflogs_cmd)

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache del p2s"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "没有缓存 p2s，无法删除。", True)
        ctx.should_finished(fflogs_cmd)

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache del p1s"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已删除副本 p1s。", True)
        ctx.should_finished(fflogs_cmd)

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps cache list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前没有缓存副本。", True)
        ctx.should_finished(fflogs_cmd)


async def test_dps_cache_permission(app: App):
    """测试 FFLOGS，没有权限设置缓存的情况"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs_cmd, plugin_data

    await plugin_data.config.set("token", "test")

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/dps cache del p2s"), user_id=10000
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "抱歉，你没有权限设置缓存。", True)
        ctx.should_finished(fflogs_cmd)


async def test_dps_bind(app: App):
    """测试绑定角色"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs_cmd, plugin_data

    await plugin_data.config.set("token", "test")

    # 查询自己的绑定角色
    async with app.test_matcher(fflogs_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/dps me"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.at(10)
            + "抱歉，你没有绑定最终幻想14的角色。\n请使用\n/dps me 角色名 服务器名\n绑定自己的角色。",
            True,
        )
        ctx.should_finished(fflogs_cmd)

    # 查询别人的绑定角色
    async with app.test_matcher(fflogs_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/dps" + MessageSegment.at(10))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.at(10) + "抱歉，该用户没有绑定最终幻想14的角色。",
            True,
        )
        ctx.should_finished(fflogs_cmd)

    # 绑定角色
    async with app.test_matcher(fflogs_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/dps me name server"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, MessageSegment.at(10) + "角色绑定成功！", True)
        ctx.should_finished(fflogs_cmd)

    # 再次查询
    async with app.test_matcher(fflogs_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/dps me"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.at(10) + "你当前绑定的角色：\n角色：name\n服务器：server",
            True,
        )
        ctx.should_finished(fflogs_cmd)

    async with app.test_matcher(fflogs_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/dps" + MessageSegment.at(10))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.at(10) + "当前绑定的角色：\n角色：name\n服务器：server",
            True,
        )
        ctx.should_finished(fflogs_cmd)


@respx.mock(assert_all_called=True)
async def test_dps_character_rankings(
    app: App,
    respx_mock: MockRouter,
    fflogs_data: dict[str, Any],
    fflogs_character_rankings: dict[str, Any],
):
    """测试角色排行榜"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs, fflogs_cmd, plugin_data

    await plugin_data.config.set("token", "test")
    await fflogs.set_character(1, "name", "server")

    fflogs_data_mock = respx_mock.get(
        "https://raw.githubusercontent.com/he0119/CoolQBot/master/src/plugins/ff14/fflogs_data.json"
    ).mock(return_value=httpx.Response(200, json=fflogs_data))
    user_dps_mock = respx_mock.get(
        "https://cn.fflogs.com/v1/rankings/character/name/server/CN?zone=29&encounter=65&metric=rdps&api_key=test"
    ).mock(return_value=httpx.Response(200, json=fflogs_character_rankings))

    # 直接 @ 用户查询
    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(
            message=Message("/dps e1s" + MessageSegment.at(10))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "伊甸零式希望乐园 觉醒之章1 name-server 的排名(rdps)\n白魔法师(17624/24314) 27.51% 4790.83",
            True,
        )
        ctx.should_finished(fflogs_cmd)

    # 查询自己的角色
    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps e1s me"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "伊甸零式希望乐园 觉醒之章1 name-server 的排名(rdps)\n白魔法师(17624/24314) 27.51% 4790.83",
            True,
        )
        ctx.should_finished(fflogs_cmd)

    # 通过输入角色名和服务器名查询对应角色
    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps e1s name server"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "伊甸零式希望乐园 觉醒之章1 name-server 的排名(rdps)\n白魔法师(17624/24314) 27.51% 4790.83",
            True,
        )
        ctx.should_finished(fflogs_cmd)

    assert fflogs_data_mock.call_count == 1
    assert user_dps_mock.call_count == 3


async def test_dps_character_rankings_not_bind(app: App):
    """测试 @ 用户，但没有绑定角色"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs_cmd, plugin_data

    await plugin_data.config.set("token", "test")

    async with app.test_matcher(fflogs_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/dps" + MessageSegment.at(10000))
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.at(10) + "抱歉，该用户没有绑定最终幻想14的角色。",
            True,
        )
        ctx.should_finished(fflogs_cmd)


@respx.mock(assert_all_called=True)
async def test_dps_update_data(
    app: App,
    respx_mock: MockRouter,
    fflogs_data: dict[str, Any],
):
    """测试 FFLOGS，测试 @ 用户的情况"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs, fflogs_cmd, plugin_data

    await plugin_data.config.set("token", "test")
    await fflogs.set_character(2, "name", "server")

    fflogs_data_mock = respx_mock.get(
        "https://raw.githubusercontent.com/he0119/CoolQBot/master/src/plugins/ff14/fflogs_data.json"
    ).mock(return_value=httpx.Response(200, json=fflogs_data))

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps update"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "副本数据更新成功，当前版本为 6.2。", True)
        ctx.should_finished(fflogs_cmd)

    assert fflogs_data_mock.call_count == 1


@respx.mock(assert_all_called=True)
async def test_dps_job_rankings_empty(
    app: App,
    mocker: MockerFixture,
    respx_mock: MockRouter,
    fflogs_data: dict[str, Any],
    fflogs_job_rankings_empty: dict[str, Any],
):
    """测试查询职业排行榜，数据为空的情况"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs_cmd, plugin_data
    from src.plugins.ff14.plugins.ff14_fflogs.config import plugin_config

    plugin_config.fflogs_range = 2
    await plugin_data.config.set("token", "test")

    mocked_datatime = mocker.patch(
        "src.plugins.ff14.plugins.ff14_fflogs.api.datetime",
        return_value=datetime(2023, 4, 15, 0, 0, 0),
    )
    mocked_datatime.now.return_value = datetime(2023, 4, 16, 12, 0, 0)

    fflogs_data_mock = respx_mock.get(
        "https://raw.githubusercontent.com/he0119/CoolQBot/master/src/plugins/ff14/fflogs_data.json"
    ).mock(return_value=httpx.Response(200, json=fflogs_data))
    fflogs_job_rankings_mock = respx_mock.get(
        "https://cn.fflogs.com/v1/rankings/encounter/65?metric=rdps&difficulty=0&spec=13&page=1&filter=date.1681488000000.1681574400000&api_key=test"
    ).mock(return_value=httpx.Response(200, json=fflogs_job_rankings_empty))
    fflogs_job_rankings_mock_now = respx_mock.get(
        "https://cn.fflogs.com/v1/rankings/encounter/65?metric=rdps&difficulty=0&spec=13&page=1&filter=date.1681401600000.1681488000000&api_key=test"
    ).mock(return_value=httpx.Response(200, json=fflogs_job_rankings_empty))

    # 使用职业昵称查询
    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps e1s 白魔"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "网站里没有数据，请稍后再试", True)
        ctx.should_finished(fflogs_cmd)

    assert fflogs_data_mock.call_count == 1
    assert fflogs_job_rankings_mock.call_count == 1
    assert fflogs_job_rankings_mock_now.call_count == 1
    mocked_datatime.assert_has_calls(
        [
            mocker.call.now(),
            mocker.call(year=2023, month=4, day=15),  # type: ignore
        ]
    )


@respx.mock(assert_all_called=True)
async def test_dps_job_rankings(
    app: App,
    mocker: MockerFixture,
    respx_mock: MockRouter,
    fflogs_data: dict[str, Any],
    fflogs_job_rankings: dict[str, Any],
    fflogs_job_rankings_empty: dict[str, Any],
):
    """测试查询职业排行榜"""
    from src.plugins.ff14.plugins.ff14_fflogs import fflogs_cmd, plugin_data
    from src.plugins.ff14.plugins.ff14_fflogs.config import plugin_config

    plugin_config.fflogs_range = 2
    await plugin_data.config.set("token", "test")

    mocked_datatime = mocker.patch(
        "src.plugins.ff14.plugins.ff14_fflogs.api.datetime",
        return_value=datetime(2023, 4, 15, 0, 0, 0),
    )
    mocked_datatime.now.return_value = datetime(2023, 4, 16, 12, 0, 0)

    fflogs_data_mock = respx_mock.get(
        "https://raw.githubusercontent.com/he0119/CoolQBot/master/src/plugins/ff14/fflogs_data.json"
    ).mock(return_value=httpx.Response(200, json=fflogs_data))
    fflogs_job_rankings_15_mock = respx_mock.get(
        "https://cn.fflogs.com/v1/rankings/encounter/87?metric=rdps&difficulty=0&spec=13&page=1&filter=date.1681488000000.1681574400000&api_key=test"
    ).mock(return_value=httpx.Response(200, json=fflogs_job_rankings))
    fflogs_job_rankings_14_mock = respx_mock.get(
        "https://cn.fflogs.com/v1/rankings/encounter/87?metric=rdps&difficulty=0&spec=13&page=1&filter=date.1681401600000.1681488000000&api_key=test"
    ).mock(return_value=httpx.Response(200, json=fflogs_job_rankings_empty))

    # 使用职业名查询
    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps p8s 白魔法师"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "零式万魔殿 炼净之狱4 白魔法师 的数据(rdps)\n数据总数：86 条\n100% : 6603.57\n99% : 6603.57\n95% : 6306.06\n75% : 5523.09\n50% : 5214.54\n25% : 4892.16\n10% : 4414.67",
            True,
        )
        ctx.should_finished(fflogs_cmd)

    # 使用职业昵称查询
    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps p8s 白魔"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "零式万魔殿 炼净之狱4 白魔法师 的数据(rdps)\n数据总数：86 条\n100% : 6603.57\n99% : 6603.57\n95% : 6306.06\n75% : 5523.09\n50% : 5214.54\n25% : 4892.16\n10% : 4414.67",
            True,
        )
        ctx.should_finished(fflogs_cmd)

    # 查询 adps
    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot(base=Bot)
        event = fake_group_message_event_v11(message=Message("/dps p8s 白魔 adps"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "零式万魔殿 炼净之狱4 白魔法师 的数据(adps)\n数据总数：86 条\n100% : 7035.92\n99% : 7035.92\n95% : 6610.49\n75% : 5803.14\n50% : 5452.80\n25% : 5058.98\n10% : 4562.49",
            True,
        )
        ctx.should_finished(fflogs_cmd)

    assert fflogs_data_mock.call_count == 1
    # 第二次请求会直接使用缓存，所以不会再次请求
    assert fflogs_job_rankings_15_mock.call_count == 1
    assert fflogs_job_rankings_14_mock.call_count == 1
    mocked_datatime.assert_has_calls(
        [
            # 第一次查询
            mocker.call.now(),
            mocker.call(year=2023, month=4, day=15),
            mocker.call.now(),  # 确认15号数据是否需要缓存
            mocker.call.now(),  # 确认14号数据是否需要缓存
            # 第二次查询
            mocker.call.now(),
            mocker.call(year=2023, month=4, day=15),
            # 第三次查询
            mocker.call.now(),
            mocker.call(year=2023, month=4, day=15),
        ]  # type: ignore
    )
