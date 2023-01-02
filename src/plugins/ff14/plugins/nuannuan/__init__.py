""" 时尚品鉴 """
from nonebot.plugin import PluginMetadata

from ... import ff14
from .data_source import get_latest_nuannuan

__plugin_meta__ = PluginMetadata(
    name="时尚品鉴",
    description="获取最新的满分攻略",
    usage="获取最新的满分攻略\n/时尚品鉴",
)
nuannuan_cmd = ff14.command("nuannuan", aliases={"时尚品鉴"})


@nuannuan_cmd.handle()
async def nuannuan_handle():
    """时尚品鉴"""
    latest = await get_latest_nuannuan()
    if latest:
        await nuannuan_cmd.finish(latest)
    else:
        await nuannuan_cmd.finish("抱歉，没有找到最新的满分攻略。")
