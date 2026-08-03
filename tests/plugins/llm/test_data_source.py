"""测试群组配置与工具注册表"""

from types import SimpleNamespace

import pytest
from nonebug import App


async def test_get_model_name_denies_unconfigured_group(app: App, mocker):
    """未设置群级准入列表时默认拒绝所有模型。"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_model_name

    mocker.patch.object(
        plugin_config,
        "models",
        [ModelConfig(name="first"), ModelConfig(name="second")],
    )

    with pytest.raises(ValueError, match="本群未开放任何模型"):
        await get_model_name("QQClient_10000")


async def test_set_and_get_model_name(app: App, mocker):
    """设置后读取到群组自己的模型"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_model_name, set_available_model_names, set_model_name

    mocker.patch.object(
        plugin_config,
        "models",
        [ModelConfig(name="first"), ModelConfig(name="second")],
    )

    await set_available_model_names("QQClient_10000", ["first", "second"])
    await set_model_name("QQClient_10000", "second")

    assert await get_model_name("QQClient_10000") == "second"
    # 其他群组仍保持默认拒绝
    with pytest.raises(ValueError, match="本群未开放任何模型"):
        await get_model_name("QQClient_20000")


async def test_get_model_name_falls_back_when_removed(app: App, mocker):
    """所设模型下线后回退到第一个可用模型"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_model_name, set_available_model_names, set_model_name

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="first"), ModelConfig(name="second")])
    await set_available_model_names("QQClient_10000", ["first", "second"])
    await set_model_name("QQClient_10000", "second")

    # 模型列表变更，second 不再可用
    mocker.patch.object(plugin_config, "models", [ModelConfig(name="first")])

    assert await get_model_name("QQClient_10000") == "first"


async def test_get_model_name_without_models(app: App, mocker):
    """未配置模型时给出明确错误"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.data_source import get_model_name

    mocker.patch.object(plugin_config, "models", [])

    with pytest.raises(ValueError, match="未配置任何模型"):
        await get_model_name("QQClient_10000")


async def test_available_models_are_scoped_by_group(app: App, mocker):
    """超级管理员设置的模型准入只影响目标群，并限制默认模型选择。"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import (
        clear_available_model_names,
        get_available_model_names,
        get_model_name,
        set_available_model_names,
        set_model_name,
    )

    mocker.patch.object(
        plugin_config,
        "models",
        [ModelConfig(name="first"), ModelConfig(name="second"), ModelConfig(name="vision")],
    )

    assert await get_available_model_names("QQClient_10000") == []
    await set_available_model_names("QQClient_10000", ["vision", "second"])

    assert await get_available_model_names("QQClient_10000") == ["second", "vision"]
    assert await get_model_name("QQClient_10000") == "second"
    assert await get_available_model_names("QQClient_20000") == []
    with pytest.raises(ValueError, match="本群未启用的模型：first"):
        await set_model_name("QQClient_10000", "first")

    await clear_available_model_names("QQClient_10000")
    assert await get_available_model_names("QQClient_10000") == []


async def test_set_available_models_rejects_unknown_and_empty_lists(app: App, mocker):
    """群组准入列表拒绝未配置模型和空列表。"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="first")])

    with pytest.raises(ValueError, match="未配置的模型：missing"):
        await set_available_model_names("QQClient_10000", ["missing", "missing"])
    with pytest.raises(ValueError, match="至少需要为本群开放一个模型"):
        await set_available_model_names("QQClient_10000", [])


async def test_model_overview_reads_group_config_once(app: App, mocker):
    """模型列表所需设置通过一次群配置查询完成。"""
    from src.plugins.llm import data_source
    from src.plugins.llm.config import ModelConfig, plugin_config

    mocker.patch.object(
        plugin_config,
        "models",
        [
            ModelConfig(name="default"),
            ModelConfig(name="explain"),
            ModelConfig(name="vision", capabilities={"vision"}),
        ],
    )
    await data_source.set_available_model_names("QQClient_10000", ["default", "explain", "vision"])
    await data_source.set_model_name("QQClient_10000", "explain")
    await data_source.set_zssm_model_name("QQClient_10000", "default")
    await data_source.set_zssm_vision_model_name("QQClient_10000", "vision")
    get_config = mocker.spy(data_source, "_get_config")

    overview = await data_source.get_model_overview("QQClient_10000")

    assert overview == data_source.GroupModelOverview(
        available_model_names=["default", "explain", "vision"],
        model_name="explain",
        zssm_model_name="default",
        zssm_vision_model_name="vision",
    )
    get_config.assert_awaited_once_with("QQClient_10000")


async def test_group_zssm_models_are_independent(app: App, mocker):
    """解释模型与视觉模型按群保存，并且只能从本群开放模型中选择。"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import (
        clear_zssm_model_name,
        clear_zssm_vision_model_name,
        get_zssm_model_name,
        get_zssm_vision_model_name,
        set_available_model_names,
        set_zssm_model_name,
        set_zssm_vision_model_name,
    )

    mocker.patch.object(
        plugin_config,
        "models",
        [
            ModelConfig(name="default"),
            ModelConfig(name="explain"),
            ModelConfig(name="vision", capabilities={"vision"}),
        ],
    )
    await set_available_model_names("QQClient_10000", ["explain", "vision"])
    await set_zssm_model_name("QQClient_10000", "explain")
    await set_zssm_vision_model_name("QQClient_10000", "vision")

    assert await get_zssm_model_name("QQClient_10000") == "explain"
    assert await get_zssm_vision_model_name("QQClient_10000") == "vision"
    with pytest.raises(ValueError, match="本群未开放任何模型"):
        await get_zssm_model_name("QQClient_20000")
    assert await get_zssm_vision_model_name("QQClient_20000") == ""

    with pytest.raises(ValueError, match="未声明 vision 能力"):
        await set_zssm_vision_model_name("QQClient_10000", "explain")
    with pytest.raises(ValueError, match="本群未启用的模型：default"):
        await set_zssm_vision_model_name("QQClient_10000", "default")
    with pytest.raises(ValueError, match="本群未启用的模型：default"):
        await set_zssm_model_name("QQClient_10000", "default")

    await clear_zssm_model_name("QQClient_10000")
    assert await get_zssm_model_name("QQClient_10000") == "explain"

    await clear_zssm_vision_model_name("QQClient_10000")
    assert await get_zssm_vision_model_name("QQClient_10000") == ""
    await set_zssm_vision_model_name("QQClient_10000", "vision")

    await set_available_model_names("QQClient_10000", ["explain"])
    assert await get_zssm_vision_model_name("QQClient_10000") == ""


async def test_set_and_get_tts_model(app: App, mocker):
    """TTS 模型的设置与读取"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.data_source import get_tts_model, set_tts_model

    mocker.patch.object(plugin_config, "tts_model", "default-tts")

    assert await get_tts_model("QQClient_10000") == "default-tts"

    await set_tts_model("QQClient_10000", "custom-tts")
    assert await get_tts_model("QQClient_10000") == "custom-tts"


def test_model_config_defaults(app: App):
    """模型配置的默认值：模型名、服务地址和工具轮数。"""
    from src.plugins.llm.config import ModelConfig, ScopedConfig

    chat = ModelConfig(name="deepseek-chat")
    assert chat.model == "deepseek-chat"
    assert chat.capabilities == set()

    anthropic = ModelConfig(
        name="claude",
        provider="anthropic",
        model="claude-opus-5",
        capabilities={"vision"},
    )
    assert anthropic.model == "claude-opus-5"
    assert anthropic.capabilities == {"vision"}

    config = ScopedConfig(models=[chat, anthropic])
    assert config.max_tool_rounds == 10
    assert config.tool_notice_delay == 10.0
    assert config.tool_notice_interval == 60.0
    assert config.resolve("deepseek-chat").base_url == "https://api.deepseek.com"
    assert config.resolve("claude").base_url == "https://api.anthropic.com"


def test_legacy_zssm_resource_config_aliases(app: App):
    """旧版 zssm 外部资源配置继续映射到通用 Web 配置。"""
    from src.plugins.llm.config import ScopedConfig

    config = ScopedConfig.model_validate(
        {
            "zssm_max_resource_bytes": 1024,
            "zssm_max_resource_chars": 2048,
            "zssm_max_pdf_pages": 3,
            "zssm_resource_timeout": 4,
            "zssm_resource_proxy": "http://proxy.example.com",
            "zssm_resource_fake_ip_ranges": ["198.18.0.0/15", "198.51.100.0/24"],
        }
    )

    assert config.web_fetch_max_bytes == 1024
    assert config.web_fetch_max_chars == 2048
    assert config.web_fetch_max_pdf_pages == 3
    assert config.web_fetch_timeout == 4
    assert config.web_proxy == "http://proxy.example.com"
    assert config.web_fetch_fake_ip_ranges == ["198.18.0.0/15", "198.51.100.0/24"]


def test_resolve_falls_back_to_global(app: App, mocker):
    """模型未单独配置时回退到全局服务地址、密钥与人设"""
    from src.plugins.llm.config import ModelConfig, plugin_config

    mocker.patch.object(
        plugin_config,
        "models",
        [
            ModelConfig(name="a"),
            ModelConfig(name="b", base_url="https://model.example.com", api_key="sk-own"),
        ],
    )
    mocker.patch.object(plugin_config, "base_url", "https://global.example.com")
    mocker.patch.object(plugin_config, "api_key", "sk-global")
    mocker.patch.object(plugin_config, "prompt", "你是助手")

    assert plugin_config.resolve("a").base_url == "https://global.example.com"
    assert plugin_config.resolve("a").api_key == "sk-global"
    assert plugin_config.resolve("a").prompt == "你是助手"
    # 已单独配置的服务地址与密钥不被覆盖
    assert plugin_config.resolve("b").base_url == "https://model.example.com"
    assert plugin_config.resolve("b").api_key == "sk-own"
    # resolve 返回副本，不污染原配置
    assert plugin_config.get_model("a").base_url == ""
    assert plugin_config.get_model("a").api_key == ""


async def test_tool_registry(app: App):
    """工具注册与执行"""
    from src.plugins.llm.schemas import ToolCall
    from src.plugins.llm.tools import ToolRegistry

    registry = ToolRegistry()

    @registry.register("add", "计算两数之和")
    def add(a: int, b: int) -> str:
        """计算两数之和

        Args:
            a: 第一个数
            b: 第二个数
        """
        return str(a + b)

    params = registry.to_params()
    assert params[0].name == "add"
    assert params[0].parameters["properties"]["a"] == {"type": "integer", "description": "第一个数"}
    assert params[0].parameters["required"] == ["a", "b"]

    # 模型常把数字写成字符串，需要能容错
    result = await registry.execute(ToolCall(id="1", name="add", arguments={"a": "1", "b": 2}))
    assert result == "3"


def test_tool_registry_resolves_postponed_annotations(app: App):
    """future annotations 仍应生成正确的 JSON Schema 类型"""
    from src.plugins.llm.tools import ToolRegistry

    def configure(count: "int", enabled: "bool") -> str:
        return f"{count}:{enabled}"

    registry = ToolRegistry()
    registry.register("configure", "修改配置")(configure)

    properties = registry.to_params()[0].parameters["properties"]
    assert properties["count"]["type"] == "integer"
    assert properties["enabled"]["type"] == "boolean"


async def test_tool_registry_errors(app: App):
    """未注册工具与缺少参数时返回错误描述而非抛出异常"""
    from src.plugins.llm.schemas import ToolCall
    from src.plugins.llm.tools import ToolRegistry

    registry = ToolRegistry()

    @registry.register("greet", "打招呼")
    def greet(name: str) -> str:
        """打招呼

        Args:
            name: 名字
        """
        return f"你好，{name}"

    assert "未注册的工具" in await registry.execute(ToolCall(id="1", name="unknown", arguments={}))
    assert "缺少必填参数" in await registry.execute(ToolCall(id="2", name="greet", arguments={}))


async def test_tool_registry_logs_metadata_without_values(app: App, mocker):
    """工具日志只记录工具名、参数名和结果规模，不记录参数值或结果正文。"""
    from src.plugins.llm.schemas import ToolCall
    from src.plugins.llm.tools import ToolRegistry

    logger_info = mocker.patch("src.plugins.llm.tools.logger.info")
    registry = ToolRegistry()

    @registry.register("lookup", "查询数据")
    def lookup(query: str, api_key: str) -> str:
        return "private-result"

    result = await registry.execute(
        ToolCall(
            id="1",
            name="lookup",
            arguments={"query": "private-query", "api_key": "secret-key"},
        )
    )

    assert result == "private-result"
    log_text = " ".join(str(item) for item in logger_info.call_args_list)
    assert "lookup" in log_text
    assert "query" in log_text
    assert "api_key" in log_text
    assert "private-query" not in log_text
    assert "secret-key" not in log_text
    assert "private-result" not in log_text


def test_usage_normalizes_across_formats(app: App):
    """三种格式的用量统计归一化后可以直接相加"""
    from src.plugins.llm.schemas import Usage

    chat = Usage(input_tokens=10, output_tokens=5)
    anthropic = Usage(input_tokens=8, output_tokens=4, cache_read_tokens=2)

    total = chat + anthropic
    assert total.input_tokens == 18
    assert total.output_tokens == 9
    assert total.total_tokens == 27
    assert total.cache_read_tokens == 2


def test_split_content_extracts_think_tags(app: App):
    """兼容把推理内容混在正文 think 标签里的服务商"""
    from src.plugins.llm.handler import split_content
    from src.plugins.llm.schemas import Completion, Message

    completion = Completion(message=Message.assistant(content="<think>在想</think>你好"))
    content, reasoning = split_content(completion)

    assert content == "你好"
    assert reasoning == "在想"


def test_format_output_quotes_multiline_thinking(app: App):
    """推理内容使用 Markdown 引用块，并保留段落结构"""
    from src.plugins.llm.handler import format_output
    from src.plugins.llm.schemas import Completion, Message

    completion = Completion(message=Message.assistant(content="回答", reasoning="第一段\n\n第二段"))

    assert format_output(completion, with_thinking=True, with_statistics=False) == "> 第一段\n>\n> 第二段\n\n回答"


@pytest.mark.parametrize(
    ("adapter", "status", "expected"),
    [
        ("OneBot V11", "thinking", "424"),
        ("Discord", "done", "🎉"),
    ],
)
async def test_send_reaction_uses_adapter_emoji(app: App, mocker, adapter, status, expected):
    """QQ 使用 emoji ID，其他平台使用 Unicode emoji"""
    from src.plugins.llm.handler import send_reaction

    get_target = mocker.patch(
        "src.plugins.llm.handler.get_target",
        return_value=SimpleNamespace(adapter=adapter, private=False),
    )
    reaction = mocker.patch("src.plugins.llm.handler.message_reaction")

    await send_reaction(status, message_id="42")

    get_target.assert_called_once_with()
    reaction.assert_awaited_once_with(expected, message_id="42")


async def test_send_reaction_skips_qq_private_message(app: App, mocker):
    """QQ 私聊不支持消息 reaction，直接跳过"""
    from nonebot_plugin_alconna import SupportAdapter

    from src.plugins.llm.handler import send_reaction

    mocker.patch(
        "src.plugins.llm.handler.get_target",
        return_value=SimpleNamespace(adapter=SupportAdapter.onebot11, private=True),
    )
    reaction = mocker.patch("src.plugins.llm.handler.message_reaction")

    await send_reaction("thinking")

    reaction.assert_not_awaited()


async def test_send_reaction_failure_does_not_interrupt_response(app: App, mocker):
    """reaction 不可用时不影响后续模型请求"""
    from src.plugins.llm.handler import send_reaction

    mocker.patch("src.plugins.llm.handler.get_target", side_effect=RuntimeError("unsupported"))

    await send_reaction("thinking")
