from nonebot_plugin_datastore import get_plugin_data

from openai import AsyncOpenAI
from openai.types.beta.threads import MessageContent

from .config import plugin_config

plugin_data = get_plugin_data()

client = AsyncOpenAI(api_key=plugin_config.openai_api_key)


async def create_assistant(session_id: str):
    assistant = await client.beta.assistants.create(
        name="Assistant",
        instructions="you are a helpful assistant.",
        tools=[{"type": "code_interpreter"}],
        model=plugin_config.openai_model,
    )

    await plugin_data.config.set(f"assistant-{session_id}", assistant.id)

    return f"助手 {assistant.id} 已创建"


async def set_assistant(id: str, session_id: str):
    await plugin_data.config.set(f"assistant-{session_id}", id)

    return f"助手 {id} 已设置"


async def create_thread(session_id: str):
    thread = await client.beta.threads.create()

    await plugin_data.config.set(f"thread-{session_id}", thread.id)

    return f"会话 {thread.id} 已创建"


async def set_thread(id: str, session_id: str):
    await plugin_data.config.set(f"thread-{session_id}", id)

    return f"会话 {id} 已设置"


async def add_message_to_thread(message: str, session_id: str):
    thread_id = await plugin_data.config.get(f"thread-{session_id}")
    if not thread_id:
        return "请先创建/指定会话"

    await client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message,
    )


def get_plaintext(content: list[MessageContent]) -> str:
    return "".join([i.text.value for i in content if i.type == "text"])


async def run(session_id: str) -> str | None:
    assistant_id = await plugin_data.config.get(f"assistant-{session_id}")
    if not assistant_id:
        return "请先创建/指定助手"

    thread_id = await plugin_data.config.get(f"thread-{session_id}")
    if not thread_id:
        return "请先创建/指定会话"

    run = await client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    if run.status == "completed":
        messages = await client.beta.threads.messages.list(thread_id=thread_id)
        return get_plaintext(messages.data[0].content)
