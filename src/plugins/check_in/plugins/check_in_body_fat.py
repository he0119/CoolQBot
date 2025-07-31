from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession
from sqlalchemy import select

from src.plugins.check_in.models import BodyFatRecord, UserInfo
from src.plugins.check_in.utils import get_or_create_user_info
from src.utils.annotated import AsyncSession

__plugin_meta__ = PluginMetadata(
    name="体脂打卡",
    description="设置和查看目标体脂并记录体脂",
    usage="""查看目标体脂
/目标体脂
设置目标体脂
/目标体脂 20
记录体脂
/体脂打卡
/体脂打卡 20""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_user", "nonebot_plugin_alconna"),
)

target_body_fat_cmd = on_alconna(
    Alconna(
        "目标体脂",
        Args["target?#目标体脂（百分比）", str],
        meta=CommandMeta(
            description="设置和查看目标体脂",
            example="查看目标体脂\n/目标体脂\n设置目标体脂\n/目标体脂 20",
        ),
    ),
    aliases={"check_in.body_fat"},
    use_cmd_start=True,
    block=True,
    extensions=[TelegramSlashExtension(), DiscordSlashExtension()],
)


@target_body_fat_cmd.handle()
async def handle_first_message(
    session: AsyncSession,
    user: UserSession,
    target: Match[str],
):
    """目标体脂"""
    if target.available:
        target_body_fat_cmd.set_path_arg("target", target.result)
    else:
        target_body_fat = (
            await session.scalars(select(UserInfo.target_body_fat).where(UserInfo.user_id == user.user_id))
        ).one_or_none()
        if target_body_fat:
            await target_body_fat_cmd.finish(f"你的目标体脂是 {target_body_fat}%，继续努力哦～", at_sender=True)


@target_body_fat_cmd.got_path("target", prompt="请输入你的目标体脂哦～")
async def _(session: AsyncSession, user: UserSession, target: str):
    """目标体脂"""
    try:
        body_fat = float(target)
    except ValueError:
        await target_body_fat_cmd.reject("目标体脂只能输入数字哦，请重新输入", at_sender=True)

    if body_fat < 0 or body_fat > 100:
        await target_body_fat_cmd.reject("目标体脂只能在 0% ~ 100% 之间哦，请重新输入", at_sender=True)

    user_info = await get_or_create_user_info(user, session)
    user_info.target_body_fat = body_fat
    await session.commit()

    await target_body_fat_cmd.finish("已成功设置，你真棒哦！祝你早日达成目标～", at_sender=True)


body_fat_record_cmd = on_alconna(
    Alconna(
        "体脂打卡",
        Args["content?#体脂（百分比）", str],
        meta=CommandMeta(
            description="记录体脂",
            example="记录体脂\n/体脂打卡\n/体脂打卡 20",
        ),
    ),
    aliases={"记录体脂", "check_in.body_record"},
    use_cmd_start=True,
    block=True,
    extensions=[TelegramSlashExtension(), DiscordSlashExtension()],
)


@body_fat_record_cmd.handle()
async def _(content: Match[str]):
    """记录体脂"""
    if content.available:
        body_fat_record_cmd.set_path_arg("content", content.result)


@body_fat_record_cmd.got_path("content", prompt="今天你的体脂是多少呢？")
async def _(session: AsyncSession, user: UserSession, content: str):
    """记录体脂"""
    try:
        body_fat = float(content)
    except ValueError:
        await body_fat_record_cmd.reject("体脂只能输入数字哦，请重新输入", at_sender=True)

    if body_fat < 0 or body_fat > 100:
        await target_body_fat_cmd.reject("目标体脂只能在 0% ~ 100% 之间哦，请重新输入", at_sender=True)

    session.add(BodyFatRecord(user_id=user.user_id, body_fat=body_fat))
    await session.commit()

    await body_fat_record_cmd.finish("已成功记录，你真棒哦！祝你早日瘦成一道闪电～", at_sender=True)
