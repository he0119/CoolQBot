"""测试群组配置与工具注册表"""

from types import SimpleNamespace

import pytest
from nonebug import App


async def test_get_model_name_default(app: App, mocker):
    """未设置时回退到配置中的第一个模型"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_model_name

    mocker.patch.object(
        plugin_config,
        "models",
        [ModelConfig(name="first"), ModelConfig(name="second")],
    )

    assert await get_model_name("QQClient_10000") == "first"


async def test_set_and_get_model_name(app: App, mocker):
    """设置后读取到群组自己的模型"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_model_name, set_model_name

    mocker.patch.object(
        plugin_config,
        "models",
        [ModelConfig(name="first"), ModelConfig(name="second")],
    )

    await set_model_name("QQClient_10000", "second")

    assert await get_model_name("QQClient_10000") == "second"
    # 其他群组不受影响
    assert await get_model_name("QQClient_20000") == "first"


async def test_get_model_name_falls_back_when_removed(app: App, mocker):
    """所设模型下线后回退到第一个可用模型"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_model_name, set_model_name

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="first"), ModelConfig(name="second")])
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


async def test_set_and_get_tts_model(app: App, mocker):
    """TTS 模型的设置与读取"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.data_source import get_tts_model, set_tts_model

    mocker.patch.object(plugin_config, "tts_model", "default-tts")

    assert await get_tts_model("QQClient_10000") == "default-tts"

    await set_tts_model("QQClient_10000", "custom-tts")
    assert await get_tts_model("QQClient_10000") == "custom-tts"


def test_model_config_defaults(app: App):
    """模型配置的默认值：model 跟随 name，解析时按格式选取 base_url"""
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
    assert config.resolve("deepseek-chat").base_url == "https://api.deepseek.com"
    assert config.resolve("claude").base_url == "https://api.anthropic.com"


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
