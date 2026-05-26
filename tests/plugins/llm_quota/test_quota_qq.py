"""测试大模型额度查询命令 (QQ 适配器)"""

import httpx
import pytest
import respx
from nonebot import get_adapter
from nonebot.adapters.qq import Adapter, Bot
from nonebot.adapters.qq.config import BotInfo
from nonebug import App
from respx import MockRouter

from tests.fake import fake_group_message_event_qq


@pytest.mark.asyncio
async def test_quota_not_configured_qq(app: App):
    from src.plugins.llm_quota import quota_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(
            base=Bot, adapter=adapter, self_id="123456", bot_info=BotInfo(id="123456", token="token", secret="secret")
        )
        event = fake_group_message_event_qq(content="/quota", group_openid="10000", author__member_openid="10")

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "当前群组未配置额度查询 API，请管理员使用 /quota set 命令配置",
            True,
            at_sender=True,
        )
        ctx.should_finished(quota_cmd)


@respx.mock(assert_all_called=True)
async def test_quota_with_config_qq(app: App, respx_mock: MockRouter):
    from src.plugins.llm_quota import quota_cmd
    from src.plugins.llm_quota.data_source import set_group_api_url

    await set_group_api_url("QQAPI_10000", "https://ai.example.com/api/quotas")

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

    quotas_mock = respx_mock.get("https://ai.example.com/api/quotas").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(
            base=Bot, adapter=adapter, self_id="123456", bot_info=BotInfo(id="123456", token="token", secret="secret")
        )
        event = fake_group_message_event_qq(content="/quota", group_openid="10000", author__member_openid="10")

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "大模型剩余额度：\n  deepseek: 4.82 元",
            True,
            at_sender=True,
        )
        ctx.should_finished(quota_cmd)

    assert quotas_mock.call_count == 1


@pytest.mark.asyncio
async def test_quota_set_by_superuser_qq(app: App):
    from src.plugins.llm_quota import quota_cmd
    from src.plugins.llm_quota.data_source import get_group_api_url

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(
            base=Bot, adapter=adapter, self_id="123456", bot_info=BotInfo(id="123456", token="token", secret="secret")
        )
        event = fake_group_message_event_qq(
            content="/quota set https://ai.example.com/api/quotas",
            group_openid="10000",
            author__member_openid="10",
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "已设置额度查询 API 地址：https://ai.example.com/api/quotas",
            True,
            at_sender=True,
        )
        ctx.should_finished(quota_cmd)

    api_url = await get_group_api_url("QQAPI_10000")
    assert api_url == "https://ai.example.com/api/quotas"


@pytest.mark.asyncio
async def test_quota_remove_by_superuser_qq(app: App):
    from src.plugins.llm_quota import quota_cmd
    from src.plugins.llm_quota.data_source import get_group_api_url, set_group_api_url

    await set_group_api_url("QQAPI_10000", "https://ai.example.com/api/quotas")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(
            base=Bot, adapter=adapter, self_id="123456", bot_info=BotInfo(id="123456", token="token", secret="secret")
        )
        event = fake_group_message_event_qq(
            content="/quota remove",
            group_openid="10000",
            author__member_openid="10",
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已删除额度查询 API 配置", True, at_sender=True)
        ctx.should_finished(quota_cmd)

    api_url = await get_group_api_url("QQAPI_10000")
    assert api_url is None


@pytest.mark.asyncio
async def test_quota_remove_not_configured_qq(app: App):
    from src.plugins.llm_quota import quota_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(
            base=Bot, adapter=adapter, self_id="123456", bot_info=BotInfo(id="123456", token="token", secret="secret")
        )
        event = fake_group_message_event_qq(
            content="/quota remove",
            group_openid="10000",
            author__member_openid="10",
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "当前群组未配置额度查询 API", True, at_sender=True)
        ctx.should_finished(quota_cmd)
