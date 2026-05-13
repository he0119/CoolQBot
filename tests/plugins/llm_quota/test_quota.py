"""测试大模型额度查询命令"""

import pytest
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


@pytest.mark.asyncio
async def test_quota_not_configured(app: App):
    from src.plugins.llm_quota import quota_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/quota"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "当前群组未配置额度查询 API，请管理员使用 /quota set 命令配置",
            True,
            at_sender=True,
        )
        ctx.should_finished(quota_cmd)


@pytest.mark.asyncio
async def test_quota_with_config(app: App, mocker: MockerFixture):
    from src.plugins.llm_quota import quota_cmd
    from src.plugins.llm_quota.data_source import set_group_api_url

    await set_group_api_url("QQClient_10000", "https://ai.example.com/api/quotas")

    mock_data = {
        "buckets": [
            {
                "name": "deepseek",
                "current": 4820000000,
                "capacity": 6280000000,
                "rate": "$0.000000001/month",
                "models": ["deepseek/*"],
                "paused": False,
                "last_updated": "2026-05-13T03:09:33.5934363Z",
            }
        ]
    }

    mock_response = mocker.MagicMock()
    mock_response.json.return_value = mock_data
    mock_response.raise_for_status = mocker.MagicMock()

    mock_client = mocker.AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mocker.AsyncMock(return_value=None)

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/quota"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "大模型剩余额度：\n  deepseek: 4.82 元",
            True,
            at_sender=True,
        )
        ctx.should_finished(quota_cmd)


@pytest.mark.asyncio
async def test_quota_set_by_superuser(app: App):
    from src.plugins.llm_quota import quota_cmd
    from src.plugins.llm_quota.data_source import get_group_api_url

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/quota set https://ai.example.com/api/quotas"),
            user_id=10,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "已设置额度查询 API 地址：https://ai.example.com/api/quotas",
            True,
            at_sender=True,
        )
        ctx.should_finished(quota_cmd)

    api_url = await get_group_api_url("QQClient_10000")
    assert api_url == "https://ai.example.com/api/quotas"


@pytest.mark.asyncio
async def test_quota_remove_by_superuser(app: App):
    from src.plugins.llm_quota import quota_cmd
    from src.plugins.llm_quota.data_source import get_group_api_url, set_group_api_url

    await set_group_api_url("QQClient_10000", "https://ai.example.com/api/quotas")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/quota remove"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已删除额度查询 API 配置", True, at_sender=True)
        ctx.should_finished(quota_cmd)

    api_url = await get_group_api_url("QQClient_10000")
    assert api_url is None


@pytest.mark.asyncio
async def test_quota_remove_not_configured(app: App):
    from src.plugins.llm_quota import quota_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/quota remove"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前群组未配置额度查询 API", True, at_sender=True)
        ctx.should_finished(quota_cmd)
