"""大模型对话插件

支持 OpenAI Chat Completions / OpenAI Responses / Anthropic Messages 三种对话
API 格式，以及 OpenAI Image API 生图模型，提供多轮对话、推理内容展示、原生 Markdown、
Markdown 转图片与 TTS 语音回复。
额度查询按模型选择独立 provider，目前支持 Aperture 与 DeepSeek。
"""

from pathlib import Path

import nonebot
from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_orm")
require("nonebot_plugin_user")
require("nonebot_plugin_waiter")
require("nonebot_plugin_alconna")

from .dialogue import chat_cmd, chat_command, llm_mention
from .management import llm_cmd

__plugin_meta__ = PluginMetadata(
    name="大模型对话",
    description="接入多种大模型 API，提供智能对话与问答功能",
    usage="使用 /chat 对话（可加 -a 启用工具、-i 允许按需生图）、/draw 绘图、/llm 管理配置，也可在群聊中 @机器人 你好",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)

__all__ = ["chat_cmd", "chat_command", "llm_cmd", "llm_mention"]

_sub_plugins = nonebot.load_plugins(str((Path(__file__).parent / "plugins").resolve()))
