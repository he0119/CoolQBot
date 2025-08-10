"""音乐插件"""

from nonebot import require
from nonebot.params import Depends
from nonebot.plugin import PluginMetadata, inherit_supported_adapters

require("nonebot_plugin_alconna")
require("nonebot_plugin_user")
require("nonebot_plugin_orm")
from arclet.alconna import AllParam
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, Subcommand, UniMessage, on_alconna
from nonebot_plugin_orm import async_scoped_session
from nonebot_plugin_user import User
from sqlalchemy import select

from src.plugins.group_bind import SessionId
from src.utils.permission import SUPERUSER

from .alisten_api import SuccessResponse, api
from .models import AlistenConfig

__plugin_meta__ = PluginMetadata(
    name="音乐",
    description="通过 alisten 服务点歌",
    usage="""参数为歌曲相关信息
/music Sagitta luminis               # 搜索并点歌
/点歌 青花瓷                          # 中文别名
/music BV1Xx411c7md                  # Bilibili BV号
/music qq:song_id                    # QQ音乐（需要指定来源）
/music wy:song_id                    # 网易云音乐（需要指定来源）

配置命令（仅限超级用户）：
/alisten config set <server_url> <house_id> [house_password]  # 设置配置
/alisten config show                                          # 查看当前配置
/alisten config delete                                        # 删除配置

支持的音乐源：
- wy: 网易云音乐
- qq: QQ音乐
- db: Bilibili（支持BV号）
""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna", "nonebot_plugin_user"),
)


async def get_config(session_id: SessionId, db_session: async_scoped_session) -> AlistenConfig | None:
    """获取 alisten 配置"""
    stmt = select(AlistenConfig).where(AlistenConfig.session_id == session_id)
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


# 音乐配置管理命令
alisten_config_cmd = on_alconna(
    Alconna(
        "alisten",
        Subcommand(
            "config",
            Subcommand("set", Args["server_url", str]["house_id", str]["house_password?", str]),
            Subcommand("show"),
            Subcommand("delete"),
        ),
        meta=CommandMeta(
            description="alisten 配置管理",
            example="配置示例:\n/alisten config set http://localhost:8080 room123 password123",
        ),
    ),
    permission=SUPERUSER,
    use_cmd_start=True,
    block=True,
)


# 配置管理命令处理
@alisten_config_cmd.assign("config.set")
async def handle_config_set(
    session_id: SessionId,
    db_session: async_scoped_session,
    server_url: str,
    house_id: str,
    house_password: str = "",
    existing_config: AlistenConfig | None = Depends(get_config),
):
    """设置 alisten 配置"""
    if existing_config:
        # 更新现有配置
        existing_config.server_url = server_url
        existing_config.house_id = house_id
        existing_config.house_password = house_password
    else:
        # 创建新配置
        new_config = AlistenConfig(
            session_id=session_id,
            server_url=server_url,
            house_id=house_id,
            house_password=house_password,
        )
        db_session.add(new_config)

    await db_session.commit()

    await alisten_config_cmd.finish(
        f"alisten 配置已设置:\n"
        f"服务器地址: {server_url}\n"
        f"房间ID: {house_id}\n"
        f"房间密码: {'已设置' if house_password else '未设置'}"
    )


@alisten_config_cmd.assign("config.show")
async def handle_config_show(config: AlistenConfig | None = Depends(get_config)):
    """显示当前配置"""
    if not config:
        await alisten_config_cmd.finish("当前群组未配置 alisten 服务")

    await alisten_config_cmd.finish(
        f"当前 alisten 配置:\n"
        f"服务器地址: {config.server_url}\n"
        f"房间ID: {config.house_id}\n"
        f"房间密码: {'已设置' if config.house_password else '未设置'}"
    )


@alisten_config_cmd.assign("config.delete")
async def handle_config_delete(
    db_session: async_scoped_session,
    config: AlistenConfig | None = Depends(get_config),
):
    """删除配置"""
    if not config:
        await alisten_config_cmd.finish("当前群组未配置 alisten 服务")

    await db_session.delete(config)
    await db_session.commit()

    await alisten_config_cmd.finish("alisten 配置已删除")


music_cmd = on_alconna(
    Alconna(
        "music",
        Args["keywords?#音乐名称或信息", AllParam],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"点歌"},
    use_cmd_start=True,
    block=True,
)


@music_cmd.handle()
async def music_handle_first_receive(
    keywords: Match[UniMessage],
    config: AlistenConfig | None = Depends(get_config),
):
    # 首先检查是否有配置
    if not config:
        await music_cmd.finish("当前群组未配置 alisten 服务\n请联系管理员使用 /alisten config set 命令进行配置")

    if keywords.available:
        music_cmd.set_path_arg("keywords", keywords.result)


@music_cmd.got_path("keywords", prompt="你想听哪首歌呢？")
async def music_handle(
    user: User,
    keywords: UniMessage,
    config: AlistenConfig = Depends(get_config),
):
    """处理点歌请求"""
    name = keywords.extract_plain_text().strip()
    if not name:
        await music_cmd.reject_path("keywords", "你想听哪首歌呢？")

    source = "wy"  # 默认音乐源

    # 解析特殊格式的输入
    if ":" in name:
        # 格式如 "wy:song_id" 或 "qq:song_id"
        parts = name.split(":", 1)
        if len(parts) == 2 and parts[0] in ["wy", "qq", "db"]:
            source = parts[0]
            name = parts[1]
    elif name.startswith("BV"):
        # Bilibili BV号
        source = "db"

    result = await api.pick_music(name=name, user_name=user.name, source=source, config=config)

    if isinstance(result, SuccessResponse):
        msg = "点歌成功！歌曲已加入播放列表"
        msg += f"\n歌曲：{result.data.name}"
        source_name = {
            "wy": "网易云音乐",
            "qq": "QQ音乐",
            "db": "Bilibili",
        }.get(result.data.source, result.data.source)
        msg += f"\n来源：{source_name}"
        await music_cmd.finish(msg, at_sender=True)
    else:
        await music_cmd.finish(result.error, at_sender=True)
