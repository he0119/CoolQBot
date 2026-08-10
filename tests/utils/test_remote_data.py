import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from src.utils.remote_data import DEFAULT_USER_AGENT, RemoteDataError, RemoteDataTooLargeError, RemoteJsonData

DATA_URL = "https://example.com/data.json"


def process_data(data: Any) -> str:
    value = data["value"]
    if not isinstance(value, str):
        raise ValueError("value 必须是字符串")
    return value


def remote_data(cache_file: Path, *, max_bytes: int = 1024) -> RemoteJsonData[str]:
    return RemoteJsonData(DATA_URL, lambda: cache_file, process_data, max_bytes=max_bytes)


@respx.mock
async def test_downloads_and_caches_data(tmp_path: Path):
    cache_file = tmp_path / "cache" / "data.json"
    request = respx.get(DATA_URL).mock(return_value=httpx.Response(200, json={"value": "new"}))
    data = remote_data(cache_file)

    assert await data.data == "new"
    assert await data.data == "new"
    assert json.loads(cache_file.read_text(encoding="utf-8")) == {"value": "new"}
    assert request.call_count == 1
    assert request.calls[0].request.headers["User-Agent"] == DEFAULT_USER_AGENT


@respx.mock
async def test_concurrent_first_reads_share_one_request(tmp_path: Path):
    request = respx.get(DATA_URL).mock(return_value=httpx.Response(200, json={"value": "shared"}))
    data = remote_data(tmp_path / "data.json")

    results = await asyncio.gather(*(data.data for _ in range(5)))

    assert results == ["shared"] * 5
    assert request.call_count == 1


@respx.mock
async def test_invalid_local_cache_is_replaced(tmp_path: Path):
    cache_file = tmp_path / "data.json"
    cache_file.write_text("not json", encoding="utf-8")
    request = respx.get(DATA_URL).mock(return_value=httpx.Response(200, json={"value": "recovered"}))
    data = remote_data(cache_file)

    assert await data.data == "recovered"
    assert json.loads(cache_file.read_text(encoding="utf-8")) == {"value": "recovered"}
    assert request.call_count == 1


@respx.mock
async def test_failed_update_preserves_memory_and_disk_cache(tmp_path: Path):
    cache_file = tmp_path / "data.json"
    original = b'{"value":"old"}'
    cache_file.write_bytes(original)
    data = remote_data(cache_file)
    assert await data.data == "old"
    respx.get(DATA_URL).mock(return_value=httpx.Response(503))

    with pytest.raises(RemoteDataError, match="更新远程数据失败"):
        await data.update()

    assert await data.data == "old"
    assert cache_file.read_bytes() == original
    assert list(tmp_path.glob(".data.json.*")) == []


@respx.mock
async def test_invalid_update_preserves_cache(tmp_path: Path):
    cache_file = tmp_path / "data.json"
    original = b'{"value":"old"}'
    cache_file.write_bytes(original)
    data = remote_data(cache_file)
    assert await data.data == "old"
    respx.get(DATA_URL).mock(return_value=httpx.Response(200, json={"value": 1}))

    with pytest.raises(RemoteDataError, match="value 必须是字符串"):
        await data.update()

    assert cache_file.read_bytes() == original
    assert await data.data == "old"


@respx.mock
async def test_rejects_oversized_data(tmp_path: Path):
    cache_file = tmp_path / "data.json"
    respx.get(DATA_URL).mock(
        return_value=httpx.Response(200, content=b'{"value":"too large"}', headers={"Content-Length": "21"})
    )
    data = remote_data(cache_file, max_bytes=20)

    with pytest.raises(RemoteDataTooLargeError, match="超过 20 字节限制"):
        await data.data

    assert not cache_file.exists()
