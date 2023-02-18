""" 复读 """
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Message
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler

from src.utils.helpers import strtobool

from ... import plugin_config, recorder_obj, repeat
from .repeat_rule import need_repeat

__plugin_meta__ = PluginMetadata(
    name="复读功能",
    description="查看与设置复读功能",
    usage="""查看当前群是否启用复读功能
/repeat
启用复读功能
/repeat on
关闭复读功能
/repeat off""",
    extra={
        "adapters": ["OneBot V11"],
    },
)


# region 自动保存数据
@scheduler.scheduled_job("interval", minutes=1, id="save_recorder")
async def save_recorder():
    """每隔一分钟保存一次数据"""
    # 保存数据前先清理 msg_send_time 列表，仅保留最近 10 分钟的数据
    for group_id in plugin_config.group_id:
        recorder_obj.message_number(10, group_id)

    recorder_obj.save_data()


@scheduler.scheduled_job("cron", day=1, hour=0, minute=0, second=0, id="clear_recorder")
async def clear_recorder():
    """每个月最后一天 24 点（下月 0 点）保存记录于历史记录文件夹，并重置记录"""
    recorder_obj.save_data_to_history()
    recorder_obj.init_data()
    logger.info("记录清除完成")


# endregion
# region 复读
repeat_message = on_message(
    rule=need_repeat,
    permission=GROUP,
    priority=5,
    block=True,
)


@repeat_message.handle()
async def repeat_message_handle(event: GroupMessageEvent):
    await repeat_message.finish(event.message)


repeat_cmd = repeat.command("basic", aliases={"repeat", "复读"}, permission=GROUP)
repeat_cmd.__doc__ = """
复读

查看当前群是否启用复读功能\n/repeat\n启用复读功能\n/repeat on\n关闭复读功能\n/repeat off
"""


@repeat_cmd.handle()
async def repeat_handle(event: GroupMessageEvent, arg: Message = CommandArg()):
    args = arg.extract_plain_text()

    group_id = event.group_id

    if args and group_id:
        if strtobool(args):
            plugin_config.group_id += [group_id]
            recorder_obj.add_new_group()
            await repeat_cmd.finish("已在本群开启复读功能")
        else:
            plugin_config.group_id = [
                n for n in plugin_config.group_id if n != group_id
            ]
            await repeat_cmd.finish("已在本群关闭复读功能")
    else:
        if group_id in plugin_config.group_id:
            await repeat_cmd.finish("复读功能开启中")
        else:
            await repeat_cmd.finish("复读功能关闭中")


# endregion
