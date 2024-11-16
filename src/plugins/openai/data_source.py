from nonebot import logger
from nonebot_plugin_datastore import get_plugin_data

from openai import AsyncOpenAI
from openai.types.beta.threads import MessageContent

from .config import plugin_config

plugin_data = get_plugin_data()

client = AsyncOpenAI(api_key=plugin_config.openai_api_key)


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

        获取助手 ID，如果不存在则创建一个新的助手
        获取会话 ID，如果不存在则创建一个新的会话
        """
        self.assistant_id = await plugin_data.config.get(self.assistant_key)
        if not self.assistant_id:
            self.assistant_id = await self.create_assistant()

        self.thread_id = await plugin_data.config.get(self.thread_key)
        if not self.thread_id:
            self.thread_id = await self.create_thread()

        logger.debug(f"assistant: {self.assistant_id}, thread: {self.thread_id}")

    async def create_assistant(self):
        assistant = await client.beta.assistants.create(
            name="Assistant",
            instructions="you are a helpful assistant.",
            tools=[{"type": "code_interpreter"}],
            model=plugin_config.openai_model,
        )

        await plugin_data.config.set(self.assistant_key, self.assistant_id)

        logger.debug(f"assistant created: {assistant.id}")
        return assistant.id

    async def create_thread(self) -> str:
        thread = await client.beta.threads.create()

        await plugin_data.config.set(self.thread_key, self.thread_id)

        logger.debug(f"thread created: {thread.id}")
        return thread.id

    async def set_assistant(self, id: str) -> str:
        await plugin_data.config.set(self.assistant_key, id)

        return f"助手 {id} 已设置"

    async def set_thread(self, id: str) -> str:
        await plugin_data.config.set(self.thread_key, id)

        return f"会话 {id} 已设置"

    async def add_message_to_thread(self, message: str) -> str | None:
        if not self.thread_id:
            return "请先创建/指定会话"

        await client.beta.threads.messages.create(
            thread_id=self.thread_id,
            role="user",
            content=message,
        )

    async def run(self) -> str | None:
        if not self.assistant_id:
            return "请先创建/指定助手"

        if not self.thread_id:
            return "请先创建/指定会话"

        run = await client.beta.threads.runs.create_and_poll(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id,
        )

        if run.status == "completed":
            messages = await client.beta.threads.messages.list(thread_id=self.thread_id)
            return self.get_plaintext(messages.data[0].content)
        else:
            return "网络繁忙，请稍后再试"

    @staticmethod
    def get_plaintext(content: list[MessageContent]) -> str:
        return "".join([i.text.value for i in content if i.type == "text"])
