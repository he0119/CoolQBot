from nonebot.params import Arg, Depends
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.typing import T_State
from nonebot_plugin_user import UserSession
from sqlalchemy import select

from src.utils.annotated import AsyncSession, OptionalPlainTextArgs, PlainTextArgs
from src.utils.helpers import parse_str

from .. import check_in
from ..models import BodyFatRecord, UserInfo
from ..utils import get_or_create_user_info

__plugin_meta__ = PluginMetadata(
    name="体脂打卡",
    description="设置和查看目标体脂并记录体脂",
    usage="""查看目标体脂
/目标体脂
设置目标体脂
/目标体脂 20
记录体脂
/体脂打卡
/体制打卡 20""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_user"),
)

target_body_fat_cmd = check_in.command("body_fat", aliases={"目标体脂"})


@target_body_fat_cmd.handle()
async def handle_first_message(
    state: T_State,
    session: AsyncSession,
    user: UserSession,
    content: OptionalPlainTextArgs,
):
    """目标体脂"""
    if content:
        state["content"] = content
    else:
        target_body_fat = (
            await session.scalars(
                select(UserInfo.target_body_fat).where(UserInfo.user_id == user.user_id)
            )
        ).one_or_none()
        if target_body_fat:
            await target_body_fat_cmd.finish(
                f"你的目标体脂是 {target_body_fat}%，继续努力哦～", at_sender=True
            )


@target_body_fat_cmd.got(
    "content", prompt="请输入你的目标体脂哦～", parameterless=[Depends(parse_str("content"))]
)
async def _(
    session: AsyncSession,
    user: UserSession,
    content: str = Arg(),
):
    """目标体脂"""
    if not content:
        await target_body_fat_cmd.reject("目标体脂不能为空，请重新输入", at_sender=True)

    try:
        body_fat = float(content)
    except ValueError:
        await target_body_fat_cmd.reject("目标体脂只能输入数字哦，请重新输入", at_sender=True)

    if body_fat < 0 or body_fat > 100:
        await target_body_fat_cmd.reject("目标体脂只能在 0% ~ 100% 之间哦，请重新输入", at_sender=True)

    user_info = await get_or_create_user_info(user, session)
    user_info.target_body_fat = body_fat
    await session.commit()

    await target_body_fat_cmd.finish("已成功设置，你真棒哦！祝你早日达成目标～", at_sender=True)


body_fat_record_cmd = check_in.command("body_record", aliases={"记录体脂", "体脂打卡"})


@body_fat_record_cmd.handle()
async def _(state: T_State, content: PlainTextArgs):
    """记录体脂"""
    state["content"] = content


@body_fat_record_cmd.got(
    "content", prompt="今天你的体脂是多少呢？", parameterless=[Depends(parse_str("content"))]
)
async def _(
    session: AsyncSession,
    user: UserSession,
    content: str = Arg(),
):
    """记录体脂"""
    if not content:
        await body_fat_record_cmd.reject("体脂不能为空，请重新输入", at_sender=True)

    try:
        body_fat = float(content)
    except ValueError:
        await body_fat_record_cmd.reject("体脂只能输入数字哦，请重新输入", at_sender=True)

    if body_fat < 0 or body_fat > 100:
        await target_body_fat_cmd.reject("目标体脂只能在 0% ~ 100% 之间哦，请重新输入", at_sender=True)

    session.add(BodyFatRecord(user_id=user.user_id, body_fat=body_fat))
    await session.commit()

    await body_fat_record_cmd.finish("已成功记录，你真棒哦！祝你早日瘦成一道闪电～", at_sender=True)
