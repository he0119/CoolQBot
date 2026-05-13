"""测试大模型额度查询数据源"""

import pytest
from nonebug import App
from pytest_mock import MockerFixture


@pytest.mark.asyncio
async def test_get_group_api_url_not_configured(app: App):
    from src.plugins.llm_quota.data_source import get_group_api_url

    result = await get_group_api_url("nonexistent_session")
    assert result is None


@pytest.mark.asyncio
async def test_set_and_get_group_api_url(app: App):
    from src.plugins.llm_quota.data_source import get_group_api_url, set_group_api_url

    api_url = "https://ai.example.com/api/quotas"
    await set_group_api_url("test_session", api_url)

    result = await get_group_api_url("test_session")
    assert result == api_url


@pytest.mark.asyncio
async def test_set_group_api_url_update(app: App):
    from src.plugins.llm_quota.data_source import get_group_api_url, set_group_api_url

    await set_group_api_url("test_session", "https://old.example.com/api")
    await set_group_api_url("test_session", "https://new.example.com/api")

    result = await get_group_api_url("test_session")
    assert result == "https://new.example.com/api"


@pytest.mark.asyncio
async def test_remove_group_api_url(app: App):
    from src.plugins.llm_quota.data_source import get_group_api_url, remove_group_api_url, set_group_api_url

    await set_group_api_url("test_session", "https://ai.example.com/api/quotas")
    removed = await remove_group_api_url("test_session")

    assert removed is True
    result = await get_group_api_url("test_session")
    assert result is None


@pytest.mark.asyncio
async def test_remove_group_api_url_not_exist(app: App):
    from src.plugins.llm_quota.data_source import remove_group_api_url

    removed = await remove_group_api_url("nonexistent_session")
    assert removed is False


@pytest.mark.asyncio
async def test_get_quotas_success(app: App, mocker: MockerFixture):
    from src.plugins.llm_quota.data_source import get_quotas

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
            },
            {
                "name": "mimo-hmy",
                "current": 38854148000,
                "capacity": 45000000000,
                "rate": "$0.000000001/month",
                "models": ["mimo-hmy*/*"],
                "paused": False,
                "last_updated": "2026-05-13T03:09:33.5934363Z",
            },
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

    result = await get_quotas("https://ai.example.com/api/quotas")

    assert "大模型剩余额度：" in result
    assert "deepseek: 4.82 元" in result
    assert "mimo-hmy: 38.85 元" in result


@pytest.mark.asyncio
async def test_get_quotas_empty_buckets(app: App, mocker: MockerFixture):
    from src.plugins.llm_quota.data_source import get_quotas

    mock_data = {"buckets": []}

    mock_response = mocker.MagicMock()
    mock_response.json.return_value = mock_data
    mock_response.raise_for_status = mocker.MagicMock()

    mock_client = mocker.AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mocker.AsyncMock(return_value=None)

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    result = await get_quotas("https://ai.example.com/api/quotas")
    assert result == "未找到额度信息"


@pytest.mark.asyncio
async def test_get_quotas_http_error(app: App, mocker: MockerFixture):
    import httpx

    from src.plugins.llm_quota.data_source import get_quotas

    mock_client = mocker.AsyncMock()
    mock_client.get.side_effect = httpx.HTTPError("Connection failed")
    mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = mocker.AsyncMock(return_value=None)

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    result = await get_quotas("https://ai.example.com/api/quotas")
    assert result == "获取额度信息失败，请稍后再试"
