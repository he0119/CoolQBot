from nonebot import on_message, require
from nonebot.adapters import Event
from nonebot.params import Depends
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.rule import to_me

require("nonebot_plugin_datastore")
require("nonebot_plugin_user")
require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, on_alconna
from nonebot_plugin_user import UserSession

from src.utils.helpers import admin_permission

from .config import plugin_config
from .data_source import Assistant
from .depends import get_assistant

__plugin_meta__ = PluginMetadata(
    name="OpenAI",
    description="使用 OpenAI 进行对话",
    usage="""直接 @机器人 进行对话
创建助手
/assistant new
切换助手
/assistant 12345678
创建会话
/thread new
切换会话
/thread 12345678
""",
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna", "nonebot_plugin_user"
    ),
)


async def openai_rule(user: UserSession) -> bool:
    # 必须要有 API Key 才能使用
    if not plugin_config.openai_api_key:
        return False
    # 必须在指定的群组中才能使用
    if user.group_session_id not in plugin_config.openai_enabled_groups:
        return False

    return True


openai_message = on_message(block=True, priority=99, rule=to_me() & openai_rule)


@openai_message.handle()
async def handle_openai_message(
    event: Event,
    assistant: Assistant = Depends(get_assistant),
):
    message = await assistant.add_message_to_thread(event.get_plaintext())
    if message:
        await openai_message.finish(message)

    message = await assistant.run()
    if message:
        await openai_message.finish(message)


assistant_cmd = on_alconna(
    Alconna(
        "助手",
        Args["id?#助手 ID", str],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"assistant"},
    use_cmd_start=True,
    block=True,
    rule=openai_rule,
    permission=admin_permission(),
)


@assistant_cmd.handle()
async def assistant_handle_first_receive(id: str):
    if id:
        assistant_cmd.set_path_arg("id", id)


@assistant_cmd.got_path("id", prompt="请输入助手 ID（new 表示新建助手）")
async def assistant_handle_group_message(
    id: str,
    assistant: Assistant = Depends(get_assistant),
):
    if id == "new":
        msg = await assistant.create_assistant()
    elif id == "show":
        msg = f"当前助手 ID 为 {assistant.assistant_id}"
    else:
        msg = await assistant.set_assistant(id)
    await assistant_cmd.finish(msg)


thread_cmd = on_alconna(
    Alconna(
        "会话",
        Args["id?#会话 ID", str],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"thread"},
    use_cmd_start=True,
    block=True,
    rule=openai_rule,
    permission=admin_permission(),
)


@thread_cmd.handle()
async def thread_handle_first_receive(id: str):
    if id:
        thread_cmd.set_path_arg("id", id)


@thread_cmd.got_path("id", prompt="请输入会话 ID（new 表示新建会话）")
async def thread_handle_group_message(
    id: str,
    assistant: Assistant = Depends(get_assistant),
):
    if id == "new":
        msg = await assistant.create_thread()
    elif id == "show":
        msg = f"当前会话 ID 为 {assistant.thread_id}"
    else:
        msg = await assistant.set_thread(id)
    await thread_cmd.finish(msg)
