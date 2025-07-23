"""壁画插件

支持收藏和查看壁画
还支持搜索壁画

收藏时应该通过回复图片来收藏 比如 /post 我从来不说壁画
查看壁画时可以通过 /bihua 我从来不说壁画，这个时候会发送我之前收藏的对应图片
搜索壁画时可以通过 /bihua_search 关键词 来搜索壁画，返回相关壁画的名称列表

同时收藏壁画时，应该记录壁画的 hash 值，避免重复收藏同一张壁画。还应该记录谁收藏的壁画，还有创建时间，方便后续管理和查询
"""

from nonebot import require
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_orm")
require("nonebot_plugin_user")
require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import (
    Alconna,
    Args,
    CommandMeta,
    Image,
    UniMessage,
    on_alconna,
)
from nonebot_plugin_user import UserSession, get_user_by_id

from src.utils.helpers import admin_permission

from .data_source import BihuaService

__plugin_meta__ = PluginMetadata(
    name="壁画收藏",
    description="收藏、查看和搜索壁画",
    usage="""收藏壁画（回复图片）
/post 壁画名称
查看壁画
/bihua 壁画名称
搜索壁画
/bihua_search 关键词
查看所有壁画
/bihua_list
删除壁画
/bihua_delete 壁画名称
统计收藏数量
/bihua_count""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)

bihua_service = BihuaService()

# 收藏壁画命令
post_cmd = on_alconna(
    Alconna(
        "post",
        Args["name", str]["image", Image],
        meta=CommandMeta(
            description="收藏壁画",
            example="发送图片和命令\n/post 我从来不说壁画 [图片]",
        ),
    ),
    use_cmd_start=True,
    block=True,
)


@post_cmd.handle()
async def _(user: UserSession, name: str, image: Image):
    if not image.url:
        await post_cmd.finish("无法获取图片URL")

    try:
        # 下载图片数据
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(image.url)
            image_data = response.content

        # 保存壁画
        await bihua_service.add_bihua(
            user_id=user.user.id, group_id=user.group_session_id, name=name, image_data=image_data, image_url=image.url
        )
        await post_cmd.finish(f"壁画 '{name}' 收藏成功！")

    except ValueError as e:
        await post_cmd.finish(f"收藏失败：{e}")
    except Exception as e:
        await post_cmd.finish(f"收藏失败：{e}")


# 查看壁画命令
bihua_cmd = on_alconna(
    Alconna(
        "bihua",
        Args["name", str],
        meta=CommandMeta(
            description="查看壁画",
            example="查看壁画\n/bihua 我从来不说壁画",
        ),
    ),
    use_cmd_start=True,
    block=True,
)


@bihua_cmd.handle()
async def _(user: UserSession, name: str):
    bihua = await bihua_service.get_bihua_by_name(name, user.group_session_id)
    if not bihua:
        await bihua_cmd.finish(f"未找到壁画 '{name}'")

    # 获取收藏者信息
    collector = await get_user_by_id(bihua.user_id)

    # 构建响应消息
    msg = UniMessage()
    msg += f"壁画：{bihua.name}\n"
    msg += f"收藏者：{collector.name}\n"
    msg += f"收藏时间：{bihua.created_at:%Y-%m-%d %H:%M}\n"

    # 发送图片
    if bihua.image_url:
        msg += Image(url=bihua.image_url)
    elif bihua.image_data:
        # 如果有本地数据，直接发送
        msg += Image(raw=bihua.image_data)

    await bihua_cmd.finish(msg)


# 搜索壁画命令
search_cmd = on_alconna(
    Alconna(
        "bihua_search",
        Args["keyword", str],
        meta=CommandMeta(
            description="搜索壁画",
            example="搜索壁画\n/bihua_search 关键词",
        ),
    ),
    use_cmd_start=True,
    block=True,
)


@search_cmd.handle()
async def _(user: UserSession, keyword: str):
    bihua_list = await bihua_service.search_bihua(keyword, user.group_session_id)

    if not bihua_list:
        await search_cmd.finish(f"未找到包含 '{keyword}' 的壁画")

    # 构建结果列表
    result_lines = [f"搜索到 {len(bihua_list)} 个相关壁画："]
    for bihua in bihua_list:
        collector = await get_user_by_id(bihua.user_id)
        result_lines.append(f"• {bihua.name} (收藏者: {collector.name})")

    await search_cmd.finish("\n".join(result_lines))


# 查看所有壁画命令
list_cmd = on_alconna(
    Alconna(
        "bihua_list",
        meta=CommandMeta(
            description="查看所有壁画",
            example="查看所有壁画\n/bihua_list",
        ),
    ),
    use_cmd_start=True,
    block=True,
)


@list_cmd.handle()
async def _(user: UserSession):
    bihua_list = await bihua_service.get_all_bihua(user.group_session_id)

    if not bihua_list:
        await list_cmd.finish("当前群组还没有收藏任何壁画")

    # 构建结果列表
    result_lines = [f"群组共有 {len(bihua_list)} 个壁画："]
    for bihua in bihua_list:
        collector = await get_user_by_id(bihua.user_id)
        result_lines.append(f"• {bihua.name} (收藏者: {collector.name})")

    await list_cmd.finish("\n".join(result_lines))


# 删除壁画命令
delete_cmd = on_alconna(
    Alconna(
        "bihua_delete",
        Args["name", str],
        meta=CommandMeta(
            description="删除壁画（只能删除自己收藏的）",
            example="删除壁画\n/bihua_delete 我从来不说壁画",
        ),
    ),
    use_cmd_start=True,
    block=True,
)


@delete_cmd.handle()
async def _(user: UserSession, name: str):
    try:
        await bihua_service.delete_bihua(name, user.group_session_id, user.user.id)
        await delete_cmd.finish(f"壁画 '{name}' 删除成功！")
    except ValueError as e:
        await delete_cmd.finish(f"删除失败：{e}")


# 统计收藏数量命令
count_cmd = on_alconna(
    Alconna(
        "bihua_count",
        meta=CommandMeta(
            description="统计各用户收藏的壁画数量",
            example="统计收藏数量\n/bihua_count",
        ),
    ),
    permission=admin_permission(),
    use_cmd_start=True,
    block=True,
)


@count_cmd.handle()
async def _(user: UserSession):
    count_data = await bihua_service.get_user_bihua_count(user.group_session_id)

    if not count_data:
        await count_cmd.finish("当前群组还没有收藏任何壁画")

    # 构建统计结果
    result_lines = ["壁画收藏统计："]
    for user_id, count in count_data:
        collector = await get_user_by_id(user_id)
        result_lines.append(f"• {collector.name}: {count} 个")

    await count_cmd.finish("\n".join(result_lines))
