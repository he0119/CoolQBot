"""Probe selective plugin loading without the suite's all-plugins fixture."""

import asyncio
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import nonebot
import pytest
import respx
from nonebot.adapters.onebot.v11 import Adapter

PLUGIN_ROOT = "src.plugins."
BUSINESS_PLUGINS = ("weather", "morning", "ff14")
BUSINESS_TOOLS = {
    "query_weather",
    "query_holiday_status",
    "query_ff14_item_price",
    "query_ff14_fashion_report",
    "query_fflogs_character_ranking",
}


def _run_probe(scenario: str, data_dir: Path) -> str:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-B", str(Path(__file__).resolve()), scenario, str(data_dir)],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root), "PYTHONUTF8": "1"},
        capture_output=True,
        encoding="utf-8",
        check=False,
        timeout=60,
    )
    logs = result.stdout + result.stderr
    assert result.returncode == 0, logs
    return logs


@pytest.mark.parametrize(
    "scenario",
    ["business-only", "invalid-llm", "llm-first", "business-first", "llm-only", "failed-fflogs"],
)
def test_optional_llm_integration(tmp_path: Path, scenario: str):
    _run_probe(scenario, tmp_path)


def _load(name: str):
    plugin = nonebot.load_plugin(PLUGIN_ROOT + name)
    assert plugin is not None, name
    return plugin


async def _probe(scenario: str, data_dir: Path):
    llm = {"models": [{"name": "test-model"}], **({"max_requests": 1} if scenario == "invalid-llm" else {})}
    nonebot.init(
        _env_file=str(data_dir / ".env"),
        llm=llm,
        localstore_cache_dir=data_dir / "cache",
        localstore_config_dir=data_dir / "config",
        localstore_data_dir=data_dir / "data",
        alconna_cache_message=False,
        **({"fflogs_cache_time": "invalid"} if scenario == "failed-fflogs" else {}),
    )
    nonebot.get_driver().register_adapter(Adapter)

    if scenario in {"llm-first", "llm-only", "failed-fflogs"}:
        _load("llm")
        await _assert_no_business_tools()
    elif scenario == "invalid-llm":
        assert nonebot.load_plugin(PLUGIN_ROOT + "llm") is None

    if scenario == "llm-only":
        assert all(PLUGIN_ROOT + name not in sys.modules for name in BUSINESS_PLUGINS)
        return

    for name in BUSINESS_PLUGINS:
        _load(name)
    if scenario in {"business-only", "business-first"}:
        assert not any(name == PLUGIN_ROOT + "llm" or name.startswith(PLUGIN_ROOT + "llm.") for name in sys.modules)
    if scenario == "invalid-llm":
        assert nonebot.get_plugin_by_module_name(PLUGIN_ROOT + "llm") is None
    if scenario == "business-first":
        _load("llm")

    await _assert_business_queries(
        through_llm=scenario in {"llm-first", "business-first", "failed-fflogs"},
        fflogs_loaded=scenario != "failed-fflogs",
    )


async def _assert_no_business_tools():
    from src.plugins.llm.schemas import ToolCall
    from src.plugins.llm.tools import registry

    assert {"web_search", "web_fetch"} <= set(registry.names())
    assert BUSINESS_TOOLS.isdisjoint(registry.names())
    assert BUSINESS_TOOLS.isdisjoint(param.name for param in registry.to_params())
    call = ToolCall(id="unloaded", name="query_weather", arguments={"location": "利姆萨·罗敏萨"})
    assert await registry.execute(call) == "错误：未注册的工具 query_weather"


async def _assert_business_queries(*, through_llm: bool, fflogs_loaded: bool):
    from src.plugins.ff14.plugins.ff14_price import price_cmd
    from src.plugins.ff14.plugins.ff14_price.data_source import get_item_price
    from src.plugins.morning.plugins.morning_greeting import morning_cmd
    from src.plugins.morning.plugins.morning_greeting.data_source import get_moring_message
    from src.plugins.weather import get_weather_of_location, weather_cmd

    assert all(matcher.plugin is not None for matcher in (weather_cmd, morning_cmd, price_cmd))
    today = date.today()
    location = "利姆萨·罗敏萨"
    item_name = "测试裙"
    holiday = "今天就是测试节，好好玩吧！"
    price = f"{item_name} 在市场的价格是:\n1234*2  服务器: 测试服\n数据更新时间:"
    with respx.mock:
        respx.get("https://bot-docs.hehome.xyz/holidays.json").respond(
            json={str(today.year): {today.isoformat(): {"name": "测试节", "duration": 1, "workdays": []}}},
        )
        respx.get(
            "https://api.ffxivteamcraft.com/search",
            params={"query": item_name, "type": "Item", "sort": "desc", "lang": "zh"},
        ).respond(json=[{"itemId": 123, "zh": item_name}])
        respx.get("https://universalis.app/api/v2/猫小胖/123?listings=6").respond(
            json={
                "itemID": 123,
                "lastUploadTime": 0,
                "listings": [
                    {"lastReviewTime": 0, "pricePerUnit": 1234, "quantity": 2, "worldName": "测试服", "hq": False},
                ],
            },
        )

        weather = await get_weather_of_location(location)
        assert weather.startswith("利姆萨·罗敏萨上层甲板\n当前天气：")
        assert holiday in await get_moring_message()
        assert (await get_item_price(item_name, "猫小胖")).startswith(price)

        if through_llm:
            from src.plugins.llm.schemas import ToolCall
            from src.plugins.llm.tools import registry

            expected = BUSINESS_TOOLS if fflogs_loaded else BUSINESS_TOOLS - {"query_fflogs_character_ranking"}
            assert BUSINESS_TOOLS.intersection(registry.names()) == expected
            assert BUSINESS_TOOLS.intersection(param.name for param in registry.to_params()) == expected
            call = ToolCall(id="weather", name="query_weather", arguments={"location": location})
            assert (await registry.execute(call)).startswith("利姆萨·罗敏萨上层甲板\n当前天气：")
            call = ToolCall(id="holiday", name="query_holiday_status", arguments={})
            assert await registry.execute(call) == holiday
            call = ToolCall(id="price", name="query_ff14_item_price", arguments={"item_name": item_name})
            assert (await registry.execute(call)).startswith(price)


@pytest.mark.parametrize("scenario", ["bad-chat", "bad-image", "all-invalid-models"])
def test_independent_model_loading(tmp_path: Path, scenario: str):
    logs = _run_probe(scenario, tmp_path)
    if scenario == "bad-chat":
        assert "models[0] (image_sizes_by_format:literal_error)" in logs
    elif scenario == "bad-image":
        assert "models[1] (value_error)" in logs
    assert "sensitive-model-input" not in logs
    assert "sensitive-model-key" not in logs


async def _probe_model_loading(scenario: str, data_dir: Path):
    bad_chat = {
        "name": "bad-chat",
        "api_key": "sensitive-model-key",
        "image_sizes_by_format": {"sensitive-model-input": ["960x960"]},
    }
    bad_image = {
        "name": "sensitive-model-input",
        "api_key": "sensitive-model-key",
        "provider": "chat",
        "capabilities": ["image_generation"],
    }
    if scenario == "bad-chat":
        models = [bad_chat, {"name": "good-image", "provider": "openai_images"}]
    elif scenario == "bad-image":
        models = [{"name": "good-chat"}, bad_image, {"name": "second-chat"}]
    else:
        models = [bad_chat, bad_image]

    nonebot.init(
        _env_file=str(data_dir / ".env"),
        llm={"models": models, "base_url": "https://shared.example/v1", "api_key": "inherited-key"},
        localstore_cache_dir=data_dir / "cache",
        localstore_config_dir=data_dir / "config",
        localstore_data_dir=data_dir / "data",
    )
    nonebot.get_driver().register_adapter(Adapter)

    if scenario == "all-invalid-models":
        assert nonebot.load_plugin(PLUGIN_ROOT + "llm") is None
        return

    _load("llm")
    from src.plugins.llm.config import ModelCapability, ModelConfig, plugin_config
    from src.plugins.llm.dialogue import chat_cmd, draw_cmd

    names = ["good-image"] if scenario == "bad-chat" else ["good-chat", "second-chat"]
    capability = ModelCapability.IMAGE_GENERATION if scenario == "bad-chat" else ModelCapability.TEXT
    assert chat_cmd.plugin is not None
    assert draw_cmd.plugin is not None
    assert plugin_config.get_model_names() == names
    for name in names:
        assert isinstance(plugin_config.get_model(name), ModelConfig)
        resolved = plugin_config.resolve(name)
        assert resolved.capabilities == {capability}
        assert resolved.base_url == "https://shared.example/v1"
        assert resolved.api_key == "inherited-key"


if __name__ == "__main__":
    probe = _probe_model_loading if sys.argv[1] in {"bad-chat", "bad-image", "all-invalid-models"} else _probe
    asyncio.run(probe(sys.argv[1], Path(sys.argv[2])))
