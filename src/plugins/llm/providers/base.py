"""Provider 抽象与共用工具"""

from __future__ import annotations

import json
import tomllib
from abc import ABC, abstractmethod
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Any

import httpx
from nonebot.log import logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from ..config import ModelConfig
    from ..schemas import Completion, Message, ToolParam


def _get_bot_version() -> str:
    """从项目 pyproject.toml 获取机器人版本"""
    pyproject = Path(__file__).resolve().parents[4] / "pyproject.toml"
    try:
        with pyproject.open("rb") as file:
            return str(tomllib.load(file)["project"]["version"])
    except (KeyError, OSError, tomllib.TOMLDecodeError):
        return "unknown"


USER_AGENT = f"CoolQBot/{_get_bot_version()}"
"""标识当前机器人版本的 User-Agent"""


class ProviderError(Exception):
    """调用大模型失败"""


async def iter_sse(response: httpx.Response) -> AsyncIterator[tuple[str, Any]]:
    """解析 SSE 流，产出 (事件名, 已解析的 JSON 数据)

    三种格式的 SSE 都遵循同一套行协议，差别只在事件名与数据结构：

    - Chat Completions 不发送 `event:` 行，以 `data: [DONE]` 结束
    - Responses 与 Anthropic 都发送 `event:` 行，事件名决定数据含义

    因此这里统一按行解析，事件名缺失时以空字符串表示。
    """
    event = ""
    async for line in response.aiter_lines():
        line = line.rstrip("\r")
        # 空行代表一个事件结束，重置事件名
        if not line:
            event = ""
            continue
        # 以冒号开头的是注释（心跳），直接忽略
        if line.startswith(":"):
            continue
        if ":" not in line:
            continue

        field, _, value = line.partition(":")
        value = value.lstrip()
        if field == "event":
            event = value
        elif field == "data":
            if value == "[DONE]":
                return
            try:
                yield event, json.loads(value)
            except json.JSONDecodeError as e:
                raise ProviderError("流式响应包含无效 JSON") from e


class Provider(ABC):
    """大模型 API 客户端基类

    子类只需实现请求体构造与响应解析，HTTP 交互由基类统一处理。
    """

    def __init__(self, config: ModelConfig, *, session_affinity: str = "") -> None:
        self.config = config
        self.session_affinity = session_affinity

    @property
    @abstractmethod
    def endpoint(self) -> str:
        """请求地址"""

    @abstractmethod
    def build_headers(self) -> dict[str, str]:
        """构造请求头"""

    @abstractmethod
    def build_payload(
        self,
        messages: list[Message],
        tools: list[ToolParam] | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """构造请求体"""

    @abstractmethod
    def parse_response(self, data: dict[str, Any]) -> Completion:
        """解析非流式响应"""

    @abstractmethod
    async def parse_stream(self, response: httpx.Response) -> Completion:
        """解析流式响应"""

    async def chat(self, messages: list[Message], tools: list[ToolParam] | None = None) -> Completion:
        """发起一次对话请求"""
        stream = bool(self.config.stream)
        log_id = self.session_affinity[:8] or "-"
        started_at = perf_counter()
        logger.debug(
            "LLM Provider 开始请求（会话={}，模型={}，协议={}，流式={}，消息={}，工具={}）",
            log_id,
            self.config.name,
            self.config.provider,
            stream,
            len(messages),
            len(tools or []),
        )
        payload = self.build_payload(messages, tools, stream=stream)
        headers = self.build_headers()
        headers["User-Agent"] = USER_AGENT
        if self.session_affinity:
            headers["X-Session-Affinity"] = self.session_affinity

        try:
            if stream:
                completion = await self._request_stream(payload, headers)
            else:
                completion = await self._request(payload, headers)
        except ProviderError:
            logger.warning(
                "LLM Provider 返回错误（会话={}，模型={}，协议={}，耗时={:.3f}s）",
                log_id,
                self.config.name,
                self.config.provider,
                perf_counter() - started_at,
            )
            raise
        except httpx.TimeoutException as e:
            logger.warning(
                "LLM Provider 请求超时（会话={}，模型={}，协议={}，耗时={:.3f}s）",
                log_id,
                self.config.name,
                self.config.provider,
                perf_counter() - started_at,
            )
            raise ProviderError("请求超时，请稍后重试") from e
        except httpx.HTTPError as e:
            logger.warning(
                "LLM Provider 网络请求失败（会话={}，模型={}，协议={}，错误类型={}，耗时={:.3f}s）",
                log_id,
                self.config.name,
                self.config.provider,
                type(e).__name__,
                perf_counter() - started_at,
            )
            raise ProviderError(f"网络请求失败：{e}") from e
        logger.debug(
            "LLM Provider 请求完成（会话={}，配置模型={}，实际模型={}，结束原因={}，工具调用={}，I={}，O={}，耗时={:.3f}s）",
            log_id,
            self.config.name,
            completion.model or "unknown",
            completion.finish_reason,
            len(completion.tool_calls),
            completion.usage.input_tokens,
            completion.usage.output_tokens,
            perf_counter() - started_at,
        )
        return completion

    async def _request(self, payload: dict[str, Any], headers: dict[str, str]) -> Completion:
        async with httpx.AsyncClient(proxy=self.config.proxy) as client:
            response = await client.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.config.timeout,
            )
        data = response.json()
        self.raise_for_error(data, response.status_code)
        return self.parse_response(data)

    async def _request_stream(self, payload: dict[str, Any], headers: dict[str, str]) -> Completion:
        # HTTPX 的 read timeout 限制网络静默时间，不会截断持续输出的长回复
        async with httpx.AsyncClient(proxy=self.config.proxy, timeout=self.config.timeout) as client:
            async with client.stream("POST", self.endpoint, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    await response.aread()
                    self.raise_for_error(response.json(), response.status_code)
                return await self.parse_stream(response)

    def raise_for_error(self, data: dict[str, Any], status_code: int = 200) -> None:
        """检查响应中的错误信息

        三种格式的错误体都是 `{"error": {"message": ...}}`，
        少数服务商会直接返回 `{"message": ...}`。
        """
        error = data.get("error")
        if isinstance(error, dict):
            raise ProviderError(str(error.get("message") or error))
        if isinstance(error, str):
            raise ProviderError(error)
        if status_code != 200:
            message = data.get("message") or f"HTTP {status_code}"
            raise ProviderError(str(message))
