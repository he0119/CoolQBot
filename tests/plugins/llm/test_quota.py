"""测试模型额度查询"""

import httpx
import pytest
import respx
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from respx import MockRouter

from tests.fake import fake_group_message_event_v11


@respx.mock(assert_all_called=True)
async def test_aperture_quota(app: App, respx_mock: MockRouter):
    """Aperture provider 解析纳元额度桶并支持按桶筛选"""
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.quota import get_quota

    route = respx_mock.get("https://ai.example.com/api/quotas").mock(
        return_value=httpx.Response(
            200,
            json={
                "buckets": [
                    {"name": "other", "current": 1000000000},
                    {"name": "deepseek", "current": 4820000000},
                ]
            },
        )
    )
    model = ModelConfig(
        name="deepseek-aperture",
        quota={
            "provider": "aperture",
            "api_url": "https://ai.example.com/api/quotas",
            "bucket": "deepseek",
        },
    )

    result = await get_quota(model)

    assert result == "deepseek-aperture 剩余额度：\n  deepseek: 4.82 元"
    assert route.calls[0].request.headers["User-Agent"].startswith("CoolQBot/")


@respx.mock(assert_all_called=True)
async def test_deepseek_quota(app: App, respx_mock: MockRouter):
    """DeepSeek provider 复用模型密钥并显示充值与赠金余额"""
    from src.plugins.llm.config import DEEPSEEK_QUOTA_API_URL, ModelConfig
    from src.plugins.llm.quota import get_quota

    route = respx_mock.get(DEEPSEEK_QUOTA_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "is_available": True,
                "balance_infos": [
                    {
                        "currency": "CNY",
                        "total_balance": "110.00",
                        "granted_balance": "10.00",
                        "topped_up_balance": "100.00",
                    },
                    {
                        "currency": "USD",
                        "total_balance": "15.25",
                        "granted_balance": "1.25",
                        "topped_up_balance": "14.00",
                    },
                ],
            },
        )
    )
    model = ModelConfig(
        name="deepseek",
        api_key="sk-model",
        quota={"provider": "deepseek"},
    )

    result = await get_quota(model)

    assert result == (
        "deepseek 剩余额度：\n"
        "  CNY: 110.00 元（赠金 10.00 元，充值 100.00 元）\n"
        "  USD: $15.25（赠金 $1.25，充值 $14.00）"
    )
    assert route.calls[0].request.headers["Authorization"] == "Bearer sk-model"


async def test_deepseek_quota_without_api_key(app: App):
    """DeepSeek 额度查询缺少密钥时给出明确错误"""
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.quota import QuotaError, get_quota

    model = ModelConfig(name="deepseek", quota={"provider": "deepseek"})

    with pytest.raises(QuotaError, match="未配置 API 密钥"):
        await get_quota(model)


@respx.mock(assert_all_called=True)
async def test_quota_http_error(app: App, respx_mock: MockRouter):
    """额度 API 出错时不向聊天消息泄露响应内容"""
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.quota import QuotaError, get_quota

    respx_mock.get("https://ai.example.com/api/quotas").mock(
        return_value=httpx.Response(401, json={"error": "secret detail"})
    )
    model = ModelConfig(
        name="aperture",
        quota={"provider": "aperture", "api_url": "https://ai.example.com/api/quotas"},
    )

    with pytest.raises(QuotaError, match="获取额度信息失败，请稍后再试"):
        await get_quota(model)


async def test_quota_not_configured(app: App):
    """模型未配置额度 provider 时给出明确错误"""
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.quota import QuotaError, get_quota

    with pytest.raises(QuotaError, match="模型 test-model 未配置额度查询"):
        await get_quota(ModelConfig(name="test-model"))


@respx.mock(assert_all_called=True)
async def test_llm_quota_command_uses_selected_model(app: App, respx_mock: MockRouter, mocker):
    """/llm quota 可指定模型，并调用该模型自己的额度 provider"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config

    mocker.patch.object(
        plugin_config,
        "models",
        [
            ModelConfig(name="without-quota"),
            ModelConfig(
                name="deepseek",
                api_key="sk-test",
                quota={"provider": "deepseek"},
            ),
        ],
    )
    respx_mock.get("https://api.deepseek.com/user/balance").mock(
        return_value=httpx.Response(
            200,
            json={
                "is_available": False,
                "balance_infos": [
                    {
                        "currency": "CNY",
                        "total_balance": "0.00",
                        "granted_balance": "0.00",
                        "topped_up_balance": "0.00",
                    }
                ],
            },
        )
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm quota deepseek"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "deepseek 剩余额度：\n  当前账户无可用余额\n  CNY: 0.00 元（赠金 0.00 元，充值 0.00 元）",
            True,
            at_sender=True,
        )
        ctx.should_finished(llm_cmd)


async def test_llm_quota_command_defaults_to_current_model(app: App, mocker):
    """/llm quota 默认查询群组当前模型"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_model_name

    mocker.patch.object(
        plugin_config,
        "models",
        [ModelConfig(name="first"), ModelConfig(name="current")],
    )
    await set_model_name("QQClient_10000", "current")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm quota"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "模型 current 未配置额度查询", True, at_sender=True)
        ctx.should_finished(llm_cmd)
