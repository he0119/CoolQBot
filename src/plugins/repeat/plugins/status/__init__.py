""" 状态 """
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot.plugin import PluginMetadata

from ... import repeat
from .data_source import get_status

__plugin_meta__ = PluginMetadata(
    name="状态",
    description="查看机器人状态",
    usage="""获取当前的机器人状态
/status""",
    extra={
        "adapters": ["OneBot V11"],
    },
)
status_cmd = repeat.command("status", aliases={"status", "状态"})


@status_cmd.handle()
async def status_handle(event: MessageEvent):
    group_id = event.group_id if isinstance(event, GroupMessageEvent) else None
    message = get_status(group_id)
    await status_cmd.finish(message)
