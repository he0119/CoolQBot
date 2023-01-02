""" 启动问候 """
import nonebot
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata, on_command

from src.utils.helpers import strtobool

from ... import plugin_config
from .data_source import get_first_connect_message

__plugin_meta__ = PluginMetadata(
    name="启动问候",
    description="启动时发送问候",
    usage="""开启时会在每天机器人第一次启动时发送问候

查看当前群是否开启启动问候
/hello
开启启动问候功能
/hello on
关闭启动问候功能
/hello off""",
)

driver = nonebot.get_driver()


@driver.on_bot_connect
async def hello_on_connect(bot: Bot) -> None:
    """启动时发送问候"""
    hello_str = get_first_connect_message()
    for group_id in plugin_config.hello_group_id:
        await bot.send_msg(message_type="group", group_id=group_id, message=hello_str)
    logger.info("发送首次启动的问候")


hello_cmd = on_command("hello", aliases={"问候"}, permission=GROUP)


@hello_cmd.handle()
async def hello_handle(event: GroupMessageEvent, arg: Message = CommandArg()):
    args = arg.extract_plain_text()

    group_id = event.group_id

    if args and group_id:
        if strtobool(args):
            plugin_config.hello_group_id += [group_id]
            await hello_cmd.finish("已在本群开启启动问候功能")
        else:
            plugin_config.hello_group_id = [
                n for n in plugin_config.hello_group_id if n != group_id
            ]
            await hello_cmd.finish("已在本群关闭启动问候功能")
    else:
        if group_id in plugin_config.hello_group_id:
            await hello_cmd.finish("启动问候功能开启中")
        else:
            await hello_cmd.finish("启动问候功能关闭中")
