"""Probe LLM model configuration in a fresh NoneBot process."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import nonebot
import pytest
from nonebot.adapters.onebot.v11 import Adapter

PLUGIN_ROOT = "src.plugins."


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


def _load(name: str):
    plugin = nonebot.load_plugin(PLUGIN_ROOT + name)
    assert plugin is not None, name
    return plugin


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
    asyncio.run(_probe_model_loading(sys.argv[1], Path(sys.argv[2])))
