from nonebot import logger
from nonebot_plugin_datastore import get_plugin_data

from openai import AsyncOpenAI, DefaultAsyncHttpxClient
from openai.types.beta.threads import MessageContent

from .config import plugin_config

plugin_data = get_plugin_data()

_openai_client = None
if plugin_config.openai_api_key:
    _openai_client = AsyncOpenAI(
        api_key=plugin_config.openai_api_key,
        http_client=DefaultAsyncHttpxClient(proxy=plugin_config.openai_proxy),
    )


def get_client() -> AsyncOpenAI:
    if not _openai_client:
        raise ValueError("请配置 OpenAI 的 API Key")
    return _openai_client


class Assistant:
    """助手"""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.assistant_id: str | None = None
        self.thread_id: str | None = None

    @property
    def assistant_key(self):
        return f"assistant-{self.session_id}"

    @property
    def thread_key(self):
        return f"thread-{self.session_id}"

    async def init(self):
        """初始化

        从配置中获取助手 ID，会话 ID
        """
        self.assistant_id = await plugin_data.config.get(self.assistant_key)
        self.thread_id = await plugin_data.config.get(self.thread_key)

        logger.debug(f"助手: {self.assistant_id}, 会话: {self.thread_id}")

    async def create_assistant(self):
        assistant = await get_client().beta.assistants.create(
            name="Assistant",
            instructions="you are a helpful assistant.",
            tools=[{"type": "code_interpreter"}],
            model=plugin_config.openai_model,
        )

        await plugin_data.config.set(self.assistant_key, assistant.id)

        logger.debug(f"assistant created: {assistant.id}")
        return f"助手 {assistant.id} 已创建"

    async def create_thread(self) -> str:
        thread = await get_client().beta.threads.create()

        await plugin_data.config.set(self.thread_key, thread.id)

        logger.debug(f"thread created: {thread.id}")
        return f"会话 {thread.id} 已创建"

    async def set_assistant(self, id: str) -> str:
        await plugin_data.config.set(self.assistant_key, id)

        return f"助手 {id} 已设置"

    async def set_thread(self, id: str) -> str:
        await plugin_data.config.set(self.thread_key, id)

        return f"会话 {id} 已设置"

    async def add_message_to_thread(self, message: str) -> str | None:
        if not self.thread_id:
            return "请先创建/指定会话"

        await get_client().beta.threads.messages.create(
            thread_id=self.thread_id,
            role="user",
            content=message,
        )

    async def run(self) -> str | None:
        if not self.assistant_id:
            return "请先创建/指定助手"

        if not self.thread_id:
            return "请先创建/指定会话"

        run = await get_client().beta.threads.runs.create_and_poll(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
        )

        if run.status == "completed":
            messages = await get_client().beta.threads.messages.list(
                thread_id=self.thread_id
            )
            return self.get_plaintext(messages.data[0].content)
        else:
            return "网络繁忙，请稍后再试"

    @staticmethod
    def get_plaintext(content: list[MessageContent]) -> str:
        return "".join([i.text.value for i in content if i.type == "text"])
